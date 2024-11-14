# This file enables Python to treat the directory as a Python package
from pathlib import Path
import sys

# Add the project root to Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))