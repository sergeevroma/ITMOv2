"""Check destructive assistant actions on a disposable Shop, without an HTTP server."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from service import Shop
from verify_before import PRACTICE, save


def main():
    shop = Shop()
    try:
        status, login = shop.dispatch("POST", "/login", {
            "username": "alice", "password": "learn-alice",
        }, {})
        assert status == 200
        auth = {"X-Token": login["token"]}
        root = shop.sandbox.root
        with TemporaryDirectory(prefix="practice-06-sentinel-") as directory:
            sentinel = Path(directory) / "sentinel.txt"
            sentinel.write_text("keep", encoding="utf-8")
            before = sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())
            request = {"decision": {"tool": "delete_tree", "arguments": {"path": "."}}}
            status, response = shop.dispatch("POST", "/assistant/execute", request, auth)
            result = {
                "mode": "direct Shop.dispatch on a new disposable instance; no HTTP process",
                "principal": "alice/customer",
                "request": request,
                "files_before": before,
                "status": status,
                "response": response,
                "sandbox_root_exists_after": root.exists(),
                "outside_sentinel_unchanged": sentinel.read_text(encoding="utf-8") == "keep",
            }
            assert status == 200 and not root.exists()
            assert result["outside_sentinel_unchanged"]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        output = PRACTICE / "lab" / "evidence" / "before" / ("isolated_delete_" + stamp + ".json")
        save(output, result)
        print("D-01 confirmed on disposable Shop; live service untouched:", output.relative_to(PRACTICE))
    finally:
        shop.close()


if __name__ == "__main__":
    main()
