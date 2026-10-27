"""Regression tests for security fixes described in REPORT_01.md.

These tests first exercise the vulnerable behaviors in the original service and
are expected to fail against the unpatched implementation. After fixes, they must pass.
"""

import json
import unittest
from urllib.error import HTTPError

from service import Shop


class SecurityRegressionTest(unittest.TestCase):
    def setUp(self):
        self.shop = Shop()
        self.addCleanup(self.shop.close)

    def request(self, method, path, body=None, headers=None):
        with self.shop.lock:
            return self.shop.dispatch(method, path, body or {}, headers or {})

    def login(self, username="alice", password="learn-alice"):
        status, result = self.request("POST", "/login", {"username": username, "password": password})
        self.assertEqual(status, 200)
        return {"X-Token": result["token"]}

    # --- Access control and spoofing ---

    def test_admin_export_requires_staff_session(self):
        status, result = self.request("GET", "/admin/export", headers={"X-Role": "staff"})
        # Expect 401 without a session
        self.assertEqual(status, 401, msg=f"unexpected: {result}")
        # Customer session should be 403
        alice = self.login("alice", "learn-alice")
        status, result = self.request("GET", "/admin/export", headers=alice)
        self.assertEqual(status, 403, msg=f"unexpected: {result}")

    def test_profile_requires_auth_and_own(self):
        # Guest should be rejected
        self.assertEqual(self.request("GET", "/profile?id=1")[0], 401)
        # Alice cannot read Bob's profile
        auth_a = self.login("alice", "learn-alice")
        status, result = self.request("GET", "/profile?id=2", headers=auth_a)
        self.assertEqual(status, 403, msg=f"alice must not read bob: {result}")

    def test_orders_hidden_from_guests_and_filtered(self):
        # Guest rejected
        self.assertEqual(self.request("GET", "/orders")[0], 401)
        # Alice sees only own orders
        auth_a = self.login("alice", "learn-alice")
        self.request("POST", "/orders", {"product": "chair"}, auth_a)
        status, rows = self.request("GET", "/orders", headers=auth_a)
        self.assertEqual(status, 200)
        self.assertTrue(all(r["owner"] == 1 for r in rows), rows)

    def test_files_only_own_and_no_traversal(self):
        auth_a = self.login("alice", "learn-alice")
        # Guest rejected
        self.assertEqual(self.request("GET", "/files?user=alice&path=receipt.txt")[0], 401)
        # Customer cannot traverse to private
        status, result = self.request("GET", "/files?user=alice&path=../private/operator-note.txt", headers=auth_a)
        self.assertEqual(status, 403, msg=str(result))

    # --- Integrity and validation ---

    def test_order_price_ignored_uses_catalog(self):
        auth_a = self.login("alice", "learn-alice")
        status, order = self.request("POST", "/orders", {"product": "lamp", "price": 1}, headers=auth_a)
        self.assertEqual(status, 201)
        self.assertEqual(order["price"], 1500)

    def test_sql_injection_profile_blocked(self):
        # Expect bad request on invalid id expression with auth
        auth = self.login("alice", "learn-alice")
        status, result = self.request("GET", "/profile?id=1 OR 1=1--", headers=auth)
        self.assertEqual(status, 400, msg=f"must reject injection: {result}")

    # --- Logging and diagnostics ---

    def test_debug_logs_require_staff_and_mask_secrets(self):
        # Populate logs with a login and an authenticated request
        auth_a = self.login("alice", "learn-alice")
        self.request("GET", "/profile?id=1", headers=auth_a)
        # Guest should be rejected from viewing logs
        self.assertEqual(self.request("GET", "/debug/logs")[0], 401)
        # Staff can view masked logs
        staff = self.login("staff", "learn-staff")
        status, logs = self.request("GET", "/debug/logs", headers={**staff, "X-Role": "staff"})
        self.assertEqual(status, 200)
        text = json.dumps(logs, ensure_ascii=False)
        self.assertNotIn("learn-alice", text)
        self.assertNotIn("\"X-Token\":", text)

    def test_reviews_capped_and_escaped_in_view(self):
        auth_a = self.login("alice", "learn-alice")
        # Submit potentially dangerous review
        self.assertEqual(self.request("POST", "/reviews", {"product": "chair", "text": "<script>alert(1)</script>"}, headers=auth_a)[0], 201)
        # Submit many reviews to exceed cap
        for i in range(0, 120):
            self.request("POST", "/reviews", {"product": "lamp", "text": f"r{i}"}, headers=auth_a)
        # View must not contain raw script tag
        status, html = self.request("GET", "/reviews/view", headers=auth_a)
        self.assertEqual(status, 200)
        self.assertNotIn("<script>", html)

    # --- Assistant policy ---

    def test_assistant_context_auth_and_ownership(self):
        # Guest rejected
        self.assertEqual(self.request("GET", "/assistant/context?order_id=2")[0], 401)
        # Alice cannot request Bob's order
        auth_a = self.login("alice", "learn-alice")
        self.assertEqual(self.request("GET", "/assistant/context?order_id=2", headers=auth_a)[0], 403)
        # Alice can request own order
        status, ctx = self.request("GET", "/assistant/context?order_id=1", headers=auth_a)
        self.assertEqual(status, 200)
        self.assertIn("chair", ctx["prompt"])

    def test_assistant_execute_policy(self):
        # Guest rejected
        decision_export = {"decision": {"tool": "export_profiles"}}
        self.assertEqual(self.request("POST", "/assistant/execute", decision_export)[0], 401)
        # Alice cannot export profiles
        auth_a = self.login("alice", "learn-alice")
        self.assertEqual(self.request("POST", "/assistant/execute", decision_export, headers=auth_a)[0], 403)
        # Alice cannot read private operator file
        decision_private = {"decision": {"tool": "read_file", "arguments": {"path": "private/operator-note.txt"}}}
        self.assertEqual(self.request("POST", "/assistant/execute", decision_private, headers=auth_a)[0], 403)
        # Alice can read her own receipt via assistant
        decision_receipt = {"decision": {"tool": "read_file", "arguments": {"path": "files/alice/receipt.txt"}}}
        status, result = self.request("POST", "/assistant/execute", decision_receipt, headers=auth_a)
        self.assertEqual(status, 200)
        self.assertIn("TEST_ALICE", result["content"])


if __name__ == "__main__":
    unittest.main()
