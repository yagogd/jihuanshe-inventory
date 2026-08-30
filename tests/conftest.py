"""Test bootstrap: isolate data dir and make `app` importable."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Make `app` importable regardless of pytest's rootdir handling.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Isolate all runtime artifacts (sqlite db, images, dumps) into a temp dir.
_test_data = tempfile.mkdtemp(prefix="jihuanshe_test_")
os.environ["JIHUANSHE_DATA_DIR"] = _test_data
os.environ["JIHUANSHE_ADB"] = "adb"
os.environ["JIHUANSHE_CAPTURE_IMAGES"] = "1"
