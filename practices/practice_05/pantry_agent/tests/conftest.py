import sys
from pathlib import Path


def pytest_sessionstart(session):
    # Ensure src directory is on sys.path (now modules live directly in src)
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
