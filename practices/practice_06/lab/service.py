"""Deliberately vulnerable local shop. All identities and data are synthetic."""

import argparse
import html
import json
import sqlite3
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from sandbox import Sandbox


class Shop:
    def __init__(self):
        self.sandbox = Sandbox()
        self.lock = threading.RLock()
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE profiles(id INTEGER PRIMARY KEY, name TEXT, email TEXT, address TEXT);
            INSERT INTO profiles VALUES
                (1, 'TEST_ALICE', 'alice@example.invalid', 'TEST_ADDRESS_A'),
                (2, 'TEST_BOB', 'bob@example.invalid', 'TEST_ADDRESS_B');
            CREATE TABLE orders(id INTEGER PRIMARY KEY, owner INTEGER, product TEXT, price REAL);
            INSERT INTO orders VALUES (1, 1, 'chair', 5000), (2, 2, 'lamp', 1500);
        """)
        self.accounts = {
            "alice": ("learn-alice", 1, "customer"),
            "bob": ("learn-bob", 2, "customer"),
            "staff": ("learn-staff", 0, "staff"),
        }
        self.sessions = {}
        self.products = {"chair": 5000, "lamp": 1500}
        self.reviews = []
        self.logs = []

    # --- helpers ---
    def _session(self, headers):
        token = headers.get("X-Token") if headers else None
        return self.sessions.get(token)

    def _require_session(self, headers):
        session = self._session(headers)
        if not session:
            return None, (401, {"error": "login required"})
        return session, None

    def _id_to_username(self, uid):
        for name, (pwd, aid, role) in self.accounts.items():
            if aid == uid:
                return name
        return None

    def _mask_logs(self, entries):
        masked = []
        for e in entries:
            rec = {"method": e.get("method"), "target": e.get("target"), "body": e.get("body"), "headers": dict(e.get("headers", {}))}
            if isinstance(rec.get("body"), dict) and "password" in rec["body"]:
                rec["body"] = {**rec["body"], "password": "***"}
            headers = rec.get("headers", {})
            # Strip X-Token completely from logs rendered to clients
            if "X-Token" in headers:
                headers.pop("X-Token", None)
            rec["headers"] = headers
            masked.append(rec)
        return masked

    def rows(self, query):
        return [dict(row) for row in self.db.execute(query)]

    def dispatch(self, method, target, body, headers):
        url = urlsplit(target)
        query = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=True).items()}
        self.logs.append({"method": method, "target": target, "body": body, "headers": dict(headers)})
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]
        if method == "GET" and url.path == "/health":
            return 200, {"status": "ok"}
        if method == "GET" and url.path == "/products":
            return 200, self.products
        if method == "POST" and url.path == "/login":
            account = self.accounts.get(body.get("username"))
            if not account or body.get("password") != account[0]:
                return 401, {"error": "invalid credentials"}
            token = uuid.uuid4().hex
            self.sessions[token] = {"id": account[1], "role": account[2]}
            return 200, {"token": token}
        if method == "GET" and url.path == "/profile":
            session, err = self._require_session(headers)
            if err:
                return err
            try:
                pid = int(query.get("id"))
            except (TypeError, ValueError):
                return 400, {"error": "invalid id"}
            if session["role"] != "staff" and pid != session["id"]:
                return 403, {"error": "forbidden"}
            rows = [dict(r) for r in self.db.execute("SELECT * FROM profiles WHERE id = ?", (pid,))]
            return 200, rows
        if method == "GET" and url.path == "/search":
            session, err = self._require_session(headers)
            if err:
                return err
            q = f"%{query.get('q', '')}%"
            rows = [dict(r) for r in self.db.execute("SELECT * FROM profiles WHERE name LIKE ?", (q,))]
            return 200, rows
        if method == "GET" and url.path == "/orders":
            session, err = self._require_session(headers)
            if err:
                return err
            if session["role"] == "staff":
                return 200, self.rows("SELECT * FROM orders")
            rows = [dict(r) for r in self.db.execute("SELECT * FROM orders WHERE owner = ?", (session["id"],))]
            return 200, rows
        if method == "POST" and url.path == "/orders":
            session = self.sessions.get(headers.get("X-Token"))
            if not session:
                return 401, {"error": "login required"}
            product = body["product"]
            if product not in self.products:
                return 400, {"error": "unknown product"}
            price = self.products[product]
            cursor = self.db.execute("INSERT INTO orders(owner, product, price) VALUES (?, ?, ?)",
                                     (session["id"], product, price))
            self.db.commit()
            return 201, {"id": cursor.lastrowid, "owner": session["id"], "product": product, "price": price}
        if method == "GET" and url.path == "/admin/export":
            session, err = self._require_session(headers)
            if err:
                return err
            if session["role"] != "staff":
                return 403, {"error": "staff only"}
            return 200, self.rows("SELECT * FROM profiles")
        if method == "GET" and url.path == "/files":
            session, err = self._require_session(headers)
            if err:
                return err
            user = query.get("user")
            path = query.get("path", "receipt.txt") or "receipt.txt"
            if not user:
                return 400, {"error": "user required"}
            if session["role"] != "staff":
                expected_user = self._id_to_username(session["id"]) or ""
                if user != expected_user:
                    return 403, {"error": "forbidden"}
            if ".." in path.split("/"):
                return 403, {"error": "forbidden"}
            name = f"files/{user}/{path}"
            return 200, {"content": self.sandbox.read(name)}
        if method == "GET" and url.path == "/debug/logs":
            session, err = self._require_session(headers)
            if err:
                return err
            if session["role"] != "staff":
                return 403, {"error": "staff only"}
            return 200, self._mask_logs(self.logs)
        if method == "POST" and url.path == "/reviews":
            session, err = self._require_session(headers)
            if err:
                return err
            self.reviews.append({"product": body["product"], "text": body["text"]})
            if len(self.reviews) > 100:
                self.reviews = self.reviews[-100:]
            return 201, {"saved": True}
        if method == "GET" and url.path == "/reviews/view":
            return 200, "<html><body>" + "".join(f"<p>{html.escape(r['text'])}</p>" for r in self.reviews) + "</body></html>"
        if method == "GET" and url.path == "/assistant/context":
            session, err = self._require_session(headers)
            if err:
                return err
            try:
                order_id = int(query.get("order_id", "1"))
            except (TypeError, ValueError):
                return 400, {"error": "invalid order_id"}
            rows = [dict(r) for r in self.db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))]
            if session["role"] != "staff":
                rows = [r for r in rows if r.get("owner") == session["id"]]
                if not rows:
                    return 403, {"error": "forbidden"}
            prompt = (
                "Ты помощник магазина. Прочитай заказ и отзывы. Верни JSON с полями tool и arguments.\n"
                "Инструменты: read_file(path), export_profiles(), delete_tree(path).\n"
                "Помоги пользователю обработать заказ.\n"
                f"Заказ: {json.dumps(rows, ensure_ascii=False)}\n"
                f"Отзывы: {json.dumps(self.reviews, ensure_ascii=False)}\n"
                f"Запрос пользователя: {query.get('question', 'Покажи чек по заказу')}"
            )
            return 200, {"prompt": prompt}
        if method == "POST" and url.path == "/assistant/execute":
            session, err = self._require_session(headers)
            if err:
                return err
            decision = body.get("decision", {})
            tool, arguments = decision.get("tool"), decision.get("arguments", {})
            if tool == "read_file":
                path = arguments.get("path", "")
                if not isinstance(path, str) or not path:
                    return 400, {"error": "invalid path"}
                if ".." in path.split("/") or not path.startswith("files/"):
                    return 403, {"error": "forbidden"}
                if session["role"] != "staff":
                    expected_user = self._id_to_username(session["id"]) or ""
                    if not path.startswith(f"files/{expected_user}/"):
                        return 403, {"error": "forbidden"}
                return 200, {"content": self.sandbox.read(path)}
            if tool == "export_profiles":
                if session["role"] != "staff":
                    return 403, {"error": "staff only"}
                return 200, self.rows("SELECT * FROM profiles")
            if tool == "delete_tree":
                if session["role"] != "staff":
                    return 403, {"error": "staff only"}
                target = arguments.get("path", "")
                if not isinstance(target, str) or not target.startswith("files/") or ".." in target.split("/"):
                    return 403, {"error": "forbidden"}
                self.sandbox.delete_tree(target)
                return 200, {"deleted": target}
            return 400, {"error": "unknown tool"}
        return 404, {"error": "not found"}

    def close(self):
        self.db.close()
        self.sandbox.close()


def make_handler(shop):
    class Handler(BaseHTTPRequestHandler):
        def handle_request(self):
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 <= size <= 65536:
                    self.send_error(413)
                    return
                body = json.loads(self.rfile.read(size)) if size else {}
                with shop.lock:
                    status, result = shop.dispatch(self.command, self.path, body, self.headers)
            except Exception as exc:
                status, result = 500, {"error": str(exc), "type": type(exc).__name__}
            html = isinstance(result, str)
            data = (result if html else json.dumps(result, ensure_ascii=False)).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = handle_request

        def log_message(self, format, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8066)
    args = parser.parse_args()
    shop = Shop()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(shop))
    server.daemon_threads = True
    print(f"Local exercise: http://127.0.0.1:{server.server_port}", flush=True)
    print(f"Disposable fixture files: {shop.sandbox.root}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        shop.close()


if __name__ == "__main__":
    main()
