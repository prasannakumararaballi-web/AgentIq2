"""Root entrypoint forwarding to apps.api.main:app for standard PaaS runners."""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
for p in [str(BASE_DIR), str(BASE_DIR / "packages"), str(BASE_DIR / "apps")]:
    if p not in sys.path:
        sys.path.insert(0, p)

from apps.api.main import app, create_app  # noqa: F401

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
