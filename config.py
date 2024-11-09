from dataclasses import dataclass
from typing import Set, Dict, Optional, List
from pathlib import Path

@dataclass
class ProcessorConfig:
    target_dir: Path
    output_file: Optional[str] = None
    include_tests: bool = False
    output_format: str = 'jsonl'
    max_file_size: int = 1024 * 1024
    worker_count: int = 4
    cache_enabled: bool = True
    verbose: bool = False
    optimize: bool = True
    excluded_patterns: Set[str] = None
    included_extensions: Set[str] = None

    def __post_init__(self):
        self.target_dir = Path(self.target_dir).resolve()
        
        # Setup default excluded patterns
        if self.excluded_patterns is None:
            self.excluded_patterns = {
                'node_modules', '.git', 'venv', '__pycache__', 
                'dist', 'build', '.env', '.pytest_cache',
                'output'  # Exclude our output directory
            }
            
        # Extensions will be populated by handler registry
        if self.included_extensions is None:
            self.included_extensions = set()

        # Ensure output file has correct extension
        if self.output_file and not self.output_file.endswith(self.output_format):
            self.output_file = f"{self.output_file}.{self.output_format}"