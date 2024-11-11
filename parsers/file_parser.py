from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import re
import chardet
from logging_config import setup_logger

logger = setup_logger(__name__)

@dataclass
class FilePatterns:
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
        r'\.git/',
        r'\.gitignore$',
        r'\.gitattributes$',
        r'__pycache__/',
        r'\.pytest_cache/',
        r'\.mypy_cache/',
        r'\.coverage$',
        r'\.coverage\.[0-9]+$',
        r'\.coverage-\w+$',
        r'\.pytest-cache/',
        r'.*\.py[cod]$',
        r'\.ruff_cache/',
        r'venv/',
        r'\.venv/',
        r'env/',
        r'\.env$',
        r'\.idea/',
        r'\.vscode/',
        r'\.vs/',
        r'\.sublime-workspace$',
        r'\.sublime-project$',
        r'build/',
        r'dist/',
        r'bin/',
        r'obj/',
        r'.*\.egg-info/',
        r'coverage/',
        r'\.DS_Store$',
        r'Thumbs\.db$',
        r'desktop\.ini$',
        r'node_modules/',
        r'package-lock\.json$',
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
    _patterns_initialized: bool = field(default=False, init=False)
    
    def __post_init__(self):
        try:
            if not self._patterns_initialized:
                if self.target_dir:
                    gitignore_patterns = self._parse_gitignore(self.target_dir)
                    self.ignore_patterns.update(gitignore_patterns)
                    logger.info(f'Added {len(gitignore_patterns)} patterns from .gitignore')
                
                self.compiled_test_patterns = []
                self.compiled_ignore_patterns = []
                
                for pattern in self.test_patterns:
                    try:
                        self.compiled_test_patterns.append(re.compile(pattern))
                    except re.error as e:
                        logger.warning(f'Invalid test pattern {pattern}: {str(e)}')
                
                for pattern in self.ignore_patterns:
                    try:
                        self.compiled_ignore_patterns.append(re.compile(pattern))
                    except re.error as e:
                        logger.warning(f'Invalid ignore pattern {pattern}: {str(e)}')
                
                logger.debug(f'Initialized FilePatterns with {len(self.compiled_test_patterns)} test patterns and {len(self.compiled_ignore_patterns)} ignore patterns')
                self._patterns_initialized = True
        except Exception as e:
            logger.error(f'Error in FilePatterns initialization: {str(e)}')
            self.compiled_test_patterns = []
            self.compiled_ignore_patterns = []

    def _parse_gitignore(self, repo_root: Path) -> Set[str]:
        """Parse .gitignore file and return a set of regex patterns."""
        patterns = set()
        gitignore_path = repo_root / '.gitignore'
        
        if not gitignore_path.exists():
            logger.debug('No .gitignore file found')
            return patterns

        try:
            with open(gitignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    pattern = self._convert_gitignore_to_regex(line)
                    if pattern:
                        patterns.add(pattern)
            
            logger.debug(f'Parsed {len(patterns)} patterns from .gitignore')
            return patterns
        except Exception as e:
            logger.error(f'Error parsing .gitignore: {e}')
            return set()

    def _convert_gitignore_to_regex(self, pattern: str) -> str:
        """Convert a gitignore pattern to a regex pattern."""
        try:
            if pattern.startswith('!'):
                return ''
            
            pattern = pattern.strip('/')
            is_dir = pattern.endswith('/')
            if is_dir:
                pattern = pattern[:-1]

            pattern = re.escape(pattern)
            # Convert gitignore globs to regex
            pattern = pattern.replace('\\*\\*', '.*')
            pattern = pattern.replace('\\*', '[^/]*')
            pattern = pattern.replace('\\?', '[^/]')
            
            if is_dir:
                pattern = pattern + '/'
            
            return pattern + ('$' if not is_dir else '')
        except Exception as e:
            logger.error(f'Error converting gitignore pattern {pattern}: {e}')
            return ''

    def should_ignore(self, file_path: Path) -> bool:
        """Check if a file should be ignored based on patterns."""
        str_path = str(file_path)
        return any(pattern.search(str_path) for pattern in self.compiled_ignore_patterns)

    def get_category(self, file_path: Path) -> str:
        """Get the category of a file based on its extension."""
        extension = file_path.suffix.lower()
        for category, extensions in self.file_categories.items():
            if extension in extensions:
                return category
        return 'other'

    def is_test_file(self, file_path: Path) -> bool:
        """Check if a file is a test file based on patterns."""
        str_path = str(file_path)
        return any(pattern.search(str_path) for pattern in self.compiled_test_patterns)

    def is_supported_extension(self, extension: str) -> bool:
        """Check if a file extension is supported."""
        return any(extension in extensions for extensions in self.file_categories.values())

    @classmethod
    def create_with_gitignore(cls, target_dir: Path, 
                            additional_ignore_patterns: Set[str] = None,
                            additional_categories: Dict[str, List[str]] = None) -> 'FilePatterns':
        """Create a FilePatterns instance with additional patterns and gitignore integration."""
        # Create instance without initializing patterns
        instance = cls(target_dir=None)  # Don't pass target_dir yet
        
        # Update patterns and categories first
        if additional_ignore_patterns:
            instance.ignore_patterns.update(additional_ignore_patterns)
        
        if additional_categories:
            for category, extensions in additional_categories.items():
                if category in instance.file_categories:
                    instance.file_categories[category].extend(extensions)
                else:
                    instance.file_categories[category] = extensions
        
        # Now set the target_dir and initialize patterns
        instance.target_dir = target_dir
        instance.__post_init__()  # This will only run once due to _patterns_initialized flag
        
        return instance
    
class FileParser:
    def __init__(self, patterns: Optional[FilePatterns] = None):
        self.patterns = patterns or FilePatterns()
        self.logger = setup_logger(__name__)

    def process_file(self, file_path: Path) -> Optional[Dict]:
        """Process a single file and return its metadata and content."""
        try:
            if not self.should_process_file(file_path):
                self.logger.debug(f'Skipping file: {file_path}')
                return None

            content = self._read_file_safely(file_path)
            if not content:
                self.logger.warning(f'Could not read content from {file_path}')
                return None

            category = self.patterns.get_category(file_path)
            is_test = self.patterns.is_test_file(file_path)

            return {
                'path': str(file_path),
                'category': category,
                'is_test': is_test,
                'size': file_path.stat().st_size,
                'content': content,
                'extension': file_path.suffix.lower(),
                'relative_path': str(file_path.relative_to(file_path.parent.parent))
            }
        except Exception as e:
            self.logger.error(f'Error processing file {file_path}: {str(e)}')
            raise

    def should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed."""
        try:
            if not file_path.is_file():
                return False
            if self.patterns.should_ignore(file_path):
                return False
            if not self.patterns.is_supported_extension(file_path.suffix.lower()):
                return False
            return True
        except Exception as e:
            self.logger.error(f'Error checking file {file_path}: {str(e)}')
            return False

    def _read_file_safely(self, file_path: Path) -> Optional[str]:
        """Read file content with proper encoding detection."""
        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                encoding = result['encoding'] or 'utf-8'

            # Try to read with detected encoding
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                # Fallback encodings if detection fails
                for enc in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        with open(file_path, 'r', encoding=enc) as f:
                            return f.read()
                    except UnicodeDecodeError:
                        continue
                
                self.logger.error(f'Failed to read {file_path} with any encoding')
                return None
        except Exception as e:
            self.logger.error(f'Error reading file {file_path}: {str(e)}')
            return None

# Default patterns instance for convenience
default_patterns = FilePatterns()