from dataclasses import dataclass, field
from typing import Set, Dict, List
from pathlib import Path
import re
from logging_config import setup_logger

logger = setup_logger(__name__)

@dataclass
class FilePatterns:
    """Configuration for file patterns used in parsing and processing."""
    
    # Test-related patterns
    test_patterns: Set[str] = field(default_factory=lambda: {
        r'test_.*\.py$',           # Python test files
        r'.*_test\.py$',           # Alternative Python test files
        r'.*\.spec\.js$',          # JavaScript/TypeScript spec files
        r'.*\.test\.js$',          # JavaScript test files
        r'.*\.spec\.ts$',          # TypeScript spec files
        r'.*\.test\.ts$',          # TypeScript test files
        r'.*Test\.java$',          # Java test files
        r'.*Tests?\.cs$',          # C# test files
        r'.*Spec\.cs$',            # C# specification files
    })

    # Patterns for files to ignore
    ignore_patterns: Set[str] = field(default_factory=lambda: {
        r'\.git/',                 # Git directory
        r'\.pytest_cache/',        # Pytest cache
        r'__pycache__/',          # Python cache
        r'node_modules/',          # Node.js modules
        r'venv/',                  # Python virtual environment
        r'\.venv/',               # Alternative virtual environment
        r'\.idea/',               # JetBrains IDE files
        r'\.vscode/',             # VSCode files
        r'\.vs/',                 # Visual Studio files
        r'bin/',                  # Binary files
        r'obj/',                  # Object files
        r'dist/',                 # Distribution files
        r'build/',                # Build files
        r'coverage/',             # Coverage reports
        r'\.coverage$',           # Python coverage file
        r'\.env$',                # Environment variables
        r'\.DS_Store$',           # macOS files
        r'Thumbs\.db$',           # Windows thumbnail cache
    })

    # File categories by extension
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
        'dotnet': ['.csproj', '.fsproj', '.vbproj', '.sln'],
    })

    def __post_init__(self):
        """Compile regex patterns for better performance."""
        self.compiled_test_patterns = [re.compile(pattern) for pattern in self.test_patterns]
        self.compiled_ignore_patterns = [re.compile(pattern) for pattern in self.ignore_patterns]
        logger.debug(f"Initialized FilePatterns with {len(self.test_patterns)} test patterns and "
                    f"{len(self.ignore_patterns)} ignore patterns")

    def is_test_file(self, file_path: Path) -> bool:
        """
        Check if a file is a test file based on configured patterns.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if the file matches any test pattern
        """
        str_path = str(file_path)
        return any(pattern.search(str_path) for pattern in self.compiled_test_patterns)

    def should_ignore(self, file_path: Path) -> bool:
        """
        Check if a file should be ignored based on configured patterns.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if the file matches any ignore pattern
        """
        str_path = str(file_path)
        return any(pattern.search(str_path) for pattern in self.compiled_ignore_patterns)

    def get_category(self, file_path: Path) -> str:
        """
        Get the category of a file based on its extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: Category name or 'other' if no category matches
        """
        extension = file_path.suffix.lower()
        for category, extensions in self.file_categories.items():
            if extension in extensions:
                return category
        return 'other'

    def is_supported_extension(self, extension: str) -> bool:
        """
        Check if a file extension is supported in any category.
        
        Args:
            extension: File extension to check (including dot)
            
        Returns:
            bool: True if the extension is supported
        """
        return any(extension in extensions for extensions in self.file_categories.values())

    @classmethod
    def create_custom(cls, 
                     additional_test_patterns: Set[str] = None,
                     additional_ignore_patterns: Set[str] = None,
                     additional_categories: Dict[str, List[str]] = None) -> 'FilePatterns':
        """
        Create a FilePatterns instance with custom additional patterns.
        
        Args:
            additional_test_patterns: Additional test file patterns to include
            additional_ignore_patterns: Additional ignore patterns to include
            additional_categories: Additional file categories to include
            
        Returns:
            FilePatterns: New instance with combined patterns
        """
        instance = cls()
        
        if additional_test_patterns:
            instance.test_patterns.update(additional_test_patterns)
            instance.compiled_test_patterns.extend(
                re.compile(pattern) for pattern in additional_test_patterns
            )
            
        if additional_ignore_patterns:
            instance.ignore_patterns.update(additional_ignore_patterns)
            instance.compiled_ignore_patterns.extend(
                re.compile(pattern) for pattern in additional_ignore_patterns
            )
            
        if additional_categories:
            for category, extensions in additional_categories.items():
                if category in instance.file_categories:
                    instance.file_categories[category].extend(extensions)
                else:
                    instance.file_categories[category] = extensions

        logger.info(f"Created custom FilePatterns with {len(instance.test_patterns)} test patterns, "
                   f"{len(instance.ignore_patterns)} ignore patterns, and "
                   f"{len(instance.file_categories)} categories")
        return instance

default_patterns = FilePatterns()