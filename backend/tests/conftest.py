import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def pytest_configure():
    # Ensure settings can import (fail-fast requires a token when enabled).
    import os

    os.environ.setdefault("CCG_AUTH_ENABLED", "0")
