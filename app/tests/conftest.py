import sys
from pathlib import Path

# Make app/ importable so `import main` works when pytest runs from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
