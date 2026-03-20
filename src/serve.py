"""RunPulse web/integration workbench entry point."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.web.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=18080, debug=True)
