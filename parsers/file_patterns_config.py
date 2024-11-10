from dataclasses import dataclass, field
from typing import Set, Dict, List, Optional
from pathlib import Path
import re
from logging_config import setup_logger
from .gitignore_parser import GitIgnoreParser

logger = setup_logger(__name__)

@dataclass
class FilePatterns:
    """Configuration for file patterns used in parsing and processing."""
    target_dir: Optional[Path] = None
    test_patterns: Set[str] = field(default_factory=lambda: {
        r'test_.*\.py$',
        r'.*_test\.py$',
        r'.*\.spec\.js$',
        r'.*\.test\.js$',
        r'.*\.spec\.ts$',
        r'.*\.test\.ts$',
        r'.*Test\.java$',
        r'.*Tests?\.cs$',
        r'.*Spec\.cs$'
    })
    
    ignore_patterns: Set[str] = field(default_factory=lambda: {
        # Git and Version Control
        r'\.git/',
        r'\.gitignore$',
        r'\.gitattributes$',
        
        # Python
        r'__pycache__/',
        r'\.pytest_cache/',
        r'\.mypy_cache/',
        r'\.coverage$',
        r'\.coverage\.[0-9]+$',
        r'\.coverage-\w+$',
        r'\.pytest-cache/',
        r'.*\.py[cod]$',
        r'\.ruff_cache/',
        
        # Virtual Environments
        r'venv/',
        r'\.venv/',
        r'env/',
        r'\.env$',
        
        # IDE and Editor Files
        r'\.idea/',
        r'\.vscode/',
        r'\.vs/',
        r'\.sublime-workspace$',
        r'\.sublime-project$',
        
        # Build and Distribution
        r'build/',
        r'dist/',
        r'bin/',
        r'obj/',
        r'.*\.egg-info/',
        r'coverage/',
        
        # System Files
        r'\.DS_Store$',
        r'Thumbs\.db$',
        r'desktop\.ini$',
        
        # Node.js
        r'node_modules/',
        r'package-lock\.json$',
        
        # Temporary Files
        r'.*~$',
        r'.*\.swp$',
        r'.*\.swo$',
        r'.*\.bak$',
        r'.*\.tmp$'
    })

    file_categories: Dict[str, List[str]] = field(default_factory=lambda: {
        'python': ['.py'],
        'javascript': ['.js', '.jsx'],
        'typescript': ['.ts', '.tsx'],
        'java': ['.java'],
        'csharp': ['.cs'],
        'markup': ['.html', '.htm', '.xml', '.xaml'],
        'stylesheet': ['.css', '.scss', '.sass', '.less'],
        'config': ['.json', '.yaml', '.yml', '.toml', '.ini'],
        'documentation': ['.md', '.rst', '.txt'],
        'database': ['.sql', '.sqlite', '.db'],
        'dotnet': ['.csproj', '.fsproj', '.vbproj', '.sln']
    })

    def __post_init__(self):
        """Initialize patterns and compile regexes."""
        try:
            if self.target_dir:
                gitignore_patterns = GitIgnoreParser.parse_gitignore(self.target_dir)
                self.ignore_patterns.update(gitignore_patterns)
                logger.info(f'Added {len(gitignore_patterns)} patterns from .gitignore')

            self.compiled_test_patterns = []
            self.compiled_ignore_patterns = []

            # Safely compile test patterns
            for pattern in self.test_patterns:
                try:
                    self.compiled_test_patterns.append(re.compile(pattern))
                except re.error as e:
                    logger.warning(f'Invalid test pattern {pattern}: {str(e)}')

            # Safely compile ignore patterns
            for pattern in self.ignore_patterns:
                try:
                    self.compiled_ignore_patterns.append(re.compile(pattern))
                except re.error as e:
                    logger.warning(f'Invalid ignore pattern {pattern}: {str(e)}')

            logger.debug(f'Initialized FilePatterns with {len(self.compiled_test_patterns)} test patterns and {len(self.compiled_ignore_patterns)} ignore patterns')

        except Exception as e:
            logger.error(f'Error in FilePatterns initialization: {str(e)}')
            self.compiled_test_patterns = []
            self.compiled_ignore_patterns = []
            
    def should_ignore(self, file_path: Path) -> bool:
        """
        Check if a file should be ignored based on the patterns.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if the file should be ignored
        """
        str_path = str(file_path)
        return any(pattern.search(str_path) for pattern in self.compiled_ignore_patterns)

    def get_category(self, file_path: Path) -> str:
        """
        Get the category of a file based on its extension.
        
        Args:
            file_path: Path to the file to categorize
            
        Returns:
            str: Category name or 'other' if no category matches
        """
        extension = file_path.suffix.lower()
        for category, extensions in self.file_categories.items():
            if extension in extensions:
                return category
        return 'other'

    def is_test_file(self, file_path: Path) -> bool:
        """Check if a file is a test file."""
        str_path = str(file_path)
        return any(pattern.search(str_path) for pattern in self.compiled_test_patterns)

    def is_supported_extension(self, extension: str) -> bool:
        """Check if a file extension is supported."""
        return any(extension in extensions for extensions in self.file_categories.values())     

    @classmethod
    def create_with_gitignore(cls, target_dir: Path, additional_ignore_patterns: Set[str] = None, additional_categories: Dict[str, List[str]] = None) -> 'FilePatterns':
        """Create a FilePatterns instance that includes .gitignore patterns."""
        instance = cls(target_dir=target_dir)
        
        if additional_ignore_patterns:
            instance.ignore_patterns.update(additional_ignore_patterns)
            
        if additional_categories:
            for category, extensions in additional_categories.items():
                if category in instance.file_categories:
                    instance.file_categories[category].extend(extensions)
                else:
                    instance.file_categories[category] = extensions
                    
        return instance

# Create default instance
default_patterns = FilePatterns()