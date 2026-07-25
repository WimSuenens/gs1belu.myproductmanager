import sys
from pathlib import Path

# Make the build helper importable when pytest is run as `pytest scripts/tests`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
