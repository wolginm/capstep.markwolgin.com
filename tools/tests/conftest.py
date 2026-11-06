"""Put tools/ on sys.path so tests can import the scripts as modules.

References:
    [PYTEST-DOCS] conftest.py, https://docs.pytest.org/en/stable/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
