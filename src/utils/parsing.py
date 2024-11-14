from typing import List, Dict, Any, Optional, Set
import re
from pathlib import Path

class CodeParser:
    """Utility class for common code parsing operations."""
    
    @staticmethod
    def extract_block_content(content: str, start_pos: int, 
                            open_char: str = '{', close_char: str = '}') -> Optional[str]:
        """Extract content between matching braces or other delimiters."""
        try:
            if start_pos >= len(content):
                return None
                
            stack = []
            result = []
            pos = start_pos
            started = False
            
            while pos < len(content):
                char = content[pos]
                
                if char == open_char:
                    stack.append(char)
                    started = True
                elif char == close_char:
                    if not stack:
                        break
                    stack.pop()
                
                if started:
                    result.append(char)
                    
                if started and not stack:
                    break
                    
                pos += 1
                
            if stack:  # Unmatched delimiters
                return None
                
            return ''.join(result[1:-1])  # Remove the delimiters themselves
        except Exception:
            return None

    @staticmethod
    def find_matching_pattern(content: str, patterns: Set[str], 
                            start_pos: int = 0) -> Optional[tuple[str, int, int]]:
        """Find the first matching pattern and return (pattern, start, end)."""
        earliest_match = None
        matched_pattern = None
        
        for pattern in patterns:
            match = re.search(pattern, content[start_pos:])
            if match:
                pos = (match.start() + start_pos, match.end() + start_pos)
                if earliest_match is None or pos[0] < earliest_match[0]:
                    earliest_match = pos
                    matched_pattern = pattern
                    
        if matched_pattern and earliest_match:
            return (matched_pattern, earliest_match[0], earliest_match[1])
        return None

    @staticmethod
    def parse_parameters(params_str: str, 
                        strip_types: bool = False) -> List[Dict[str, str]]:
        """
        Parse function/method parameters.
        Returns list of dicts with 'name' and optionally 'type'.
        """
        if not params_str.strip():
            return []
            
        params = []
        current_param = []
        nesting_level = 0
        
        for char in params_str:
            if char in '<([{':
                nesting_level += 1
            elif char in '>)]}':
                nesting_level -= 1
            elif char == ',' and nesting_level == 0:
                param = ''.join(current_param).strip()
                if param:
                    params.append(CodeParser._process_parameter(param, strip_types))
                current_param = []
                continue
            current_param.append(char)
            
        # Handle last parameter
        param = ''.join(current_param).strip()
        if param:
            params.append(CodeParser._process_parameter(param, strip_types))
            
        return params

    @staticmethod
    def _process_parameter(param: str, strip_types: bool) -> Dict[str, str]:
        """Process a single parameter string into a structured format."""
        # Handle default values
        parts = param.split('=', 1)
        param = parts[0].strip()
        
        if strip_types:
            # Just get the parameter name
            name = param.split()[-1].strip()
            return {'name': name}
        else:
            # Try to separate type and name
            parts = param.split()
            if len(parts) == 1:
                return {'name': parts[0]}
            else:
                return {
                    'name': parts[-1],
                    'type': ' '.join(parts[:-1])
                }

    @staticmethod
    def find_docstring(content: str, start_pos: int = 0) -> Optional[str]:
        """Extract docstring following a declaration."""
        try:
            content = content[start_pos:].lstrip()
            
            # Single line docstring
            single_match = re.match(r'[\'\"]{3}(.*?)[\'\"]{3}', content, re.DOTALL)
            if single_match:
                return single_match.group(1).strip()
            
            # Multi-line docstring
            multi_match = re.match(r'[\'\"]{3}(.*?)[\'\"]{3}', content, re.DOTALL)
            if multi_match:
                return multi_match.group(1).strip()
                
            return None
        except Exception:
            return None

    @staticmethod
    def find_decorators(content: str, start_pos: int) -> List[str]:
        """Find decorators preceding a declaration."""
        decorators = []
        try:
            # Look backwards from start_pos to find decorators
            lines = content[:start_pos].splitlines()
            for line in reversed(lines):
                line = line.strip()
                if line.startswith('@'):
                    # Extract decorator name and arguments if present
                    decorator = line[1:]
                    paren_idx = decorator.find('(')
                    if paren_idx != -1:
                        decorator = decorator[:paren_idx].strip()
                    decorators.insert(0, decorator)
                elif line:  # Found non-empty, non-decorator line
                    break
            return decorators
        except Exception:
            return decorators