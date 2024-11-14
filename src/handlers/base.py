from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from src.core.config import LanguageConfig
from src.core.exceptions import ParsingError

@dataclass
class CodeMetrics:
    """Metrics calculated for a code file."""
    lines_of_code: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    complexity: int = 0
    max_depth: int = 0
    maintainability_index: float = 100.0

class BaseHandler(ABC):
    """Base class for language handlers."""
    def __init__(self):
        self.config = self.__class__.config

    @abstractmethod
    def analyze_code(self, content: str) -> Dict[str, Any]:
        """Analyze code content and return metrics and structural information."""
        pass

    @abstractmethod
    def clean_content(self, content: str) -> str:
        """Remove comments and normalize whitespace."""
        pass

class BaseParserMixin:
    """Common parsing functionality for all handlers."""
    
    def parse_functions(self, content: str) -> List[Dict[str, Any]]:
        """Parse function declarations from code content."""
        return []
    
    def parse_classes(self, content: str) -> List[Dict[str, Any]]:
        """Parse class declarations from code content."""
        return []
    
    def parse_imports(self, content: str) -> List[str]:
        """Parse import statements from code content."""
        return []

class JSStyleLanguageMixin:
    """Functionality specific to C-style syntax languages."""
    
    def parse_brackets(self, content: str) -> int:
        """Calculate nesting depth based on brackets."""
        depth = 0
        max_depth = 0
        for char in content:
            if char == '{':
                depth += 1
                max_depth = max(max_depth, depth)
            elif char == '}':
                depth = max(0, depth - 1)
        return max_depth
    
    def clean_comments(self, content: str, single_line: str, 
                      multi_start: Optional[str], multi_end: Optional[str]) -> str:
        """Remove comments from code content."""
        if not content:
            return ""
        
        # Remove single-line comments
        lines = []
        for line in content.splitlines():
            comment_pos = line.find(single_line)
            if comment_pos >= 0:
                line = line[:comment_pos]
            if line.strip():
                lines.append(line)
        
        content = '\n'.join(lines)
        
        # Remove multi-line comments if configured
        if multi_start and multi_end:
            start = 0
            while True:
                start_pos = content.find(multi_start, start)
                if start_pos < 0:
                    break
                end_pos = content.find(multi_end, start_pos)
                if end_pos < 0:
                    break
                content = content[:start_pos] + content[end_pos + len(multi_end):]
                start = start_pos
        
        return content