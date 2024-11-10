from pathlib import Path
from typing import Set
import re
from logging_config import setup_logger

logger = setup_logger(__name__)

class GitignorePattern:
    def __init__(self, pattern: str):
        self.raw_pattern = pattern
        self.is_negated = pattern.startswith('!')
        self.is_directory_only = pattern.endswith('/')
        
        pattern = pattern[1:] if self.is_negated else pattern
        pattern = pattern.rstrip('/')
        self.regex = self._glob_to_regex(pattern)

    def _glob_to_regex(self, pattern: str) -> re.Pattern:
        regex = ''
        if not pattern.startswith('/'):
            regex = '(?:.+/)?'
        for c in pattern:
            if c == '*':
                regex += '[^/]*'
            elif c == '?':
                regex += '[^/]'
            elif c in '.[]()+^${}|':
                regex += f'\\{c}'
            else:
                regex += c
        regex = f'^{regex}(?:/.*)?$' if self.is_directory_only else f'^{regex}$'
        return re.compile(regex)

    def matches(self, path: str) -> bool:
        return bool(self.regex.match(path))

class GitIgnoreParser:
    """Parser for .gitignore files"""
    
    @staticmethod
    def parse_gitignore(repo_root: Path) -> Set[str]:
        """
        Parse .gitignore file and return a set of patterns.
        
        Args:
            repo_root: Root directory of the repository
            
        Returns:
            Set of gitignore patterns converted to regex patterns
        """
        patterns = set()
        gitignore_path = repo_root / '.gitignore'
        
        if not gitignore_path.exists():
            logger.debug('No .gitignore file found')
            return patterns
            
        try:
            with open(gitignore_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                        
                    # Convert gitignore pattern to regex pattern
                    pattern = GitIgnoreParser._convert_to_regex(line)
                    if pattern:
                        patterns.add(pattern)
                        
            logger.debug(f'Parsed {len(patterns)} patterns from .gitignore')
            return patterns
            
        except Exception as e:
            logger.error(f'Error parsing .gitignore: {e}')
            return set()
    
    @staticmethod
    def _convert_to_regex(pattern: str) -> str:
        """Convert a gitignore pattern to a regex pattern."""
        try:
            # Handle negation
            if pattern.startswith('!'):
                return ''  # Skip negation patterns for now
                
            # Remove leading and trailing slashes
            pattern = pattern.strip('/')
            
            # Handle directory marker
            is_dir = pattern.endswith('/')
            if is_dir:
                pattern = pattern[:-1]
            
            # Escape special regex characters
            pattern = re.escape(pattern)
            
            # Convert gitignore globs to regex
            pattern = pattern.replace('\\*\\*', '.*')  # ** to .*
            pattern = pattern.replace('\\*', '[^/]*')  # * to [^/]*
            pattern = pattern.replace('\\?', '[^/]')   # ? to [^/]
            
            # Add directory marker if needed
            if is_dir:
                pattern = pattern + '/'
                
            # Add start/end markers
            return pattern + ('$' if not is_dir else '')
            
        except Exception as e:
            logger.error(f'Error converting gitignore pattern {pattern}: {e}')
            return ''

default_parser = GitIgnoreParser()