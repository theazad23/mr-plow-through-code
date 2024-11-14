# This file enables Python to treat the directory as a Python package
from pathlib import Path
import importlib.util
import sys

# Dynamically import all Python files in this directory except __init__.py
plugin_dir = Path(__file__).parent
for plugin_file in plugin_dir.glob("*.py"):
    if plugin_file.name != "__init__.py":
        module_name = f"src.handlers.plugins.{plugin_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)