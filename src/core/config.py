from dataclasses import dataclass, field
from pathlib import Path
from typing import Set, Dict, List, Optional

@dataclass
class LanguageConfig:
    """Configuration for a specific programming language."""
    name: str
    file_extensions: Set[str]
    single_line_comment: str
    multi_line_comment_start: Optional[str] = None
    multi_line_comment_end: Optional[str] = None
    test_file_patterns: Set[str] = field(default_factory=set)
    keywords: Set[str] = field(default_factory=set)
    complexity_patterns: Set[str] = field(default_factory=set)

@dataclass
class ProcessorConfig:
    """Global configuration for the code processor."""
    target_dir: Path
    output_file: Optional[str] = None
    include_tests: bool = False
    output_format: str = 'jsonl'
    max_file_size: int = 1024 * 1024  # 1MB
    worker_count: int = 4
    excluded_patterns: Set[str] = field(default_factory=lambda: {
        '.git', '__pycache__', 'node_modules', 'venv',
        'build', 'dist', '.pytest_cache', '.mypy_cache'
    })
    
    def __post_init__(self):
        self.target_dir = Path(self.target_dir).resolve()
        if self.output_file and not self.output_file.endswith(self.output_format):
            self.output_file = f'{self.output_file}.{self.output_format}'