import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

FIXTURE_DIR = Path(__file__).resolve().parent / "fixture_build"
GOLDENS = Path(__file__).resolve().parent / "goldens.json"
