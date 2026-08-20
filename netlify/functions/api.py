import os
import sys
from pathlib import Path

# Netlify functions run from a read-only deployment directory.
# Keep SQLite/config writes in the writable /tmp directory.
os.chdir('/tmp')
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mangum import Mangum
from backend.main import app
import backend.main as cms_main

cms_main.MARKET_DATABASE = '/tmp/cms_v12.db'
try:
    cms_main.strategy_manager.config_path = Path('/tmp/cms_config.yaml')
except Exception:
    pass

handler = Mangum(app, lifespan='off')
