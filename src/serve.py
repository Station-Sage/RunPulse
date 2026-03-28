"""RunPulse web/integration workbench entry point."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.web.app import create_app

app = create_app()

if __name__ == "__main__":
    import os
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=18080, debug=debug)
