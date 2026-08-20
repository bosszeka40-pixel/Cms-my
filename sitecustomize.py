"""Process-wide runtime logging for CMS server deployments.

Python imports sitecustomize automatically when it is available on sys.path.
The Docker image runs from /app, so this file is loaded before Uvicorn imports
backend.main. It intentionally configures logging only; application behavior is
not monkey-patched here.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

if os.getenv("CMS_FILE_LOGGING", "true").lower() not in {"0", "false", "no"}:
    try:
        log_dir = Path(os.getenv("CMS_LOG_DIR", "logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "cms-errors.log"
        handler = logging.FileHandler(log_file, encoding="utf-8")
        handler.setLevel(logging.ERROR)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s",
                "%Y-%m-%dT%H:%M:%S%z",
            )
        )
        root = logging.getLogger()
        root.addHandler(handler)
        root.setLevel(min(root.level or logging.WARNING, logging.ERROR))
    except Exception:
        pass
