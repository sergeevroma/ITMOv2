"""Start an isolated RoomBook demo API with a known booking."""

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import uvicorn

SKILL_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = SKILL_DIR.parents[2] / "room_booking_project"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    sys.path.insert(0, str(PROJECT_DIR))
    from app.api import create_app
    from app.models import BookingInput
    from app.storage import add_booking

    with TemporaryDirectory(prefix="roombook-audit-demo-") as folder:
        db_path = Path(folder) / "demo.sqlite3"
        fixture = json.loads((SKILL_DIR / "examples" / "schedule.json").read_text())
        saved = add_booking(
            db_path, BookingInput.model_validate(fixture).model_dump(mode="json"),
        )
        print(f'Demo booking ID {saved["id"]}: {saved}', flush=True)
        uvicorn.run(create_app(db_path), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
