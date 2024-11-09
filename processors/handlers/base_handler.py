from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Set
import re

@dataclass
class CodeMetrics:
    lines_of_code: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    complexity: int = 0
    maintainability_index: float = 100.0
    max_depth: int = 0
    
class BaseCodeHandler(ABC):
    """Base class for language-specific code handlers."""
    
    def __init__(self):
        self.single_line_comment = '//'  # Override in subclass
        self.multi_line_comment_start = '/*'  # Override in subclass
        self.multi_line_comment_end = '*/'  # Override in subclass
        
    @abstractmethod
    def analyze_code(self, content: str) -> Dict[str, Any]:
        """Analyze code content and return metrics and structural information."""
        pass
        
    @abstractmethod
    def clean_content(self, content: str) -> str:
        """Remove comments and normalize whitespace."""
        pass
        
    def count_lines(self, content: str) -> CodeMetrics:
        """Count different types of lines in the code."""
        lines = content.splitlines()
        metrics = CodeMetrics()
        metrics.lines_of_code = len(lines)
        metrics.blank_lines = sum(1 for line in lines if not line.strip())
        metrics.comment_lines = self._count_comment_lines(content)
        return metrics
    
    def _count_comment_lines(self, content: str) -> int:
        """Count comment lines using language-specific comment markers."""
        lines = content.splitlines()
        comment_count = 0
        in_multi_line = False
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            if self.multi_line_comment_start in line:
                in_multi_line = True
                comment_count += 1
                continue
                
            if in_multi_line:
                comment_count += 1
                if self.multi_line_comment_end in line:
                    in_multi_line = False
                continue
                
            if stripped.startswith(self.single_line_comment):
                comment_count += 1
                
        return comment_count
    
    def calculate_complexity(self, content: str) -> int:
        """Calculate cyclomatic complexity using a basic approach."""
        # Override in subclasses for more accurate language-specific complexity
        control_structures = len(re.findall(
            r'\b(if|else|for|while|case|switch|catch)\b', 
            content
        ))
        boolean_ops = len(re.findall(r'\b(&&|\|\|)\b', content))
        ternary_ops = len(re.findall(r'\?.*:(?![^{]*})', content))
        return max(1, control_structures + boolean_ops + ternary_ops)
    
    def calculate_max_depth(self, content: str) -> int:
        """Calculate maximum nesting depth."""
        lines = content.splitlines()
        max_depth = current_depth = 0
        
        for line in lines:
            opening = line.count('{')
            closing = line.count('}')
            current_depth += opening - closing
            max_depth = max(max_depth, current_depth)
            
        return max_depth
    
    def clean_basic_comments(self, content: str) -> str:
        """Remove comments using language-specific markers."""
        # Remove single-line comments
        content = re.sub(f'{self.single_line_comment}.*$', '', 
                        content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        if self.multi_line_comment_start and self.multi_line_comment_end:
            pattern = f'{self.multi_line_comment_start}[\s\S]*?{self.multi_line_comment_end}'
            content = re.sub(pattern, '', content)
            
        return '\n'.join(line for line in content.splitlines() if line.strip())