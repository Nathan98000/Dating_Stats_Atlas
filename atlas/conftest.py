import sys
from pathlib import Path

# Make `import atlas.*` work when pytest runs from anywhere in the repo.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
