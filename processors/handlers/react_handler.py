from typing import Dict, Any, List, Optional
import re
from .base_handler import BaseCodeHandler, CodeMetrics
from ..constants import AnalysisKeys as Keys
import logging

class ReactHandler(BaseCodeHandler):
    """Handler for React/JSX source code analysis with improved regex handling."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.single_line_comment = '//'
        self.multi_line_comment_start = '/*'
        self.multi_line_comment_end = '*/'

    def analyze_code(self, content: str) -> Dict[str, Any]:
        try:
            # First clean the content safely
            cleaned = self.clean_content(content)
            
            # Get basic metrics
            metrics = self.count_lines(content)
            
            # Analyze the cleaned content
            analysis_result = {
                Keys.SUCCESS: True,
                Keys.METRICS: self._get_metrics(cleaned, metrics),
                Keys.IMPORTS: self._collect_imports(cleaned),
                Keys.COMPONENTS: self._collect_components(cleaned),
                Keys.HOOKS: self._collect_hooks(cleaned)
            }
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing React code: {str(e)}")
            return {Keys.SUCCESS: False, Keys.ERROR: str(e)}

    def _get_metrics(self, content: str, base_metrics: CodeMetrics) -> Dict[str, Any]:
        """Calculate React-specific metrics safely."""
        try:
            base_metrics.complexity = self._calculate_react_complexity(content)
            base_metrics.max_depth = self._calculate_jsx_depth(content)
            return Keys.metrics_result(base_metrics)
        except Exception as e:
            self.logger.error(f"Error calculating metrics: {str(e)}")
            return Keys.metrics_result(CodeMetrics())

    def _calculate_react_complexity(self, content: str) -> int:
        """Calculate complexity for React components with safe regex."""
        try:
            complexity = 1  # Base complexity
            
            # Control structures
            patterns = [
                r'\bif\s*\(',           # if statements
                r'\belse\s+if\b',       # else if
                r'\bfor\s*\(',          # for loops
                r'\bwhile\s*\(',        # while loops
                r'\bswitch\s*\(',       # switch statements
                r'\bcatch\s*\(',        # catch blocks
                r'\?',                  # ternary operators
                r'&&',                  # logical AND
                r'\|\|',                # logical OR
                r'\.map\(',             # Array maps
                r'\.filter\(',          # Array filters
                r'\.reduce\(',          # Array reduces
                r'\buseEffect\(',       # useEffect hooks
                r'\buseCallback\(',     # useCallback hooks
                r'\buseMemo\('          # useMemo hooks
            ]
            
            for pattern in patterns:
                try:
                    complexity += len(re.findall(pattern, content))
                except Exception:
                    continue
                    
            return max(1, complexity)
            
        except Exception as e:
            self.logger.error(f"Error in complexity calculation: {str(e)}")
            return 1

    def _calculate_jsx_depth(self, content: str) -> int:
        """Calculate JSX nesting depth safely."""
        try:
            max_depth = 0
            current_depth = 0
            
            # Count JSX depth using bracket matching
            for char in content:
                if char == '<' and content[content.find(char) + 1:].strip()[0].isalpha():
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                elif char == '/>' or char == '</':
                    current_depth = max(0, current_depth - 1)
                    
            return max_depth
            
        except Exception as e:
            self.logger.error(f"Error calculating JSX depth: {str(e)}")
            return 0

    def _collect_imports(self, content: str) -> List[str]:
        """Collect React imports safely."""
        imports = set()
        try:
            # Match both default and named imports
            import_patterns = [
                r'import\s+(?:{[^}]+}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
                r'import\s+[\'"]([^\'"]+)[\'"]'
            ]
            
            for pattern in import_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    imports.add(match.group(1))
                    
            return sorted(list(imports))
            
        except Exception as e:
            self.logger.error(f"Error collecting imports: {str(e)}")
            return list(imports)

    def _collect_components(self, content: str) -> List[Dict[str, Any]]:
        """Collect React component information safely."""
        components = []
        try:
            # Function components (arrow and regular)
            component_patterns = [
                r'(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w+)',
                r'(?:export\s+)?(?:default\s+)?const\s+([A-Z]\w+)\s*=\s*(?:\([^)]*\))?\s*=>'
            ]
            
            for pattern in component_patterns:
                try:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        name = match.group(1)
                        components.append({
                            'name': name,
                            'type': 'functional',
                            'hooks': self._find_component_hooks(content, match.start())
                        })
                except Exception:
                    continue
                    
            return components
            
        except Exception as e:
            self.logger.error(f"Error collecting components: {str(e)}")
            return components

    def _collect_hooks(self, content: str) -> List[Dict[str, Any]]:
        """Collect React hooks usage safely."""
        hooks = []
        try:
            # Match hook calls
            hook_pattern = r'\b(use[A-Z]\w+)\s*\('
            matches = re.finditer(hook_pattern, content)
            
            for match in matches:
                hook_name = match.group(1)
                if hook_name.startswith('use'):
                    hooks.append({
                        'name': hook_name,
                        'custom': not hook_name.startswith('use')
                    })
                    
            return hooks
            
        except Exception as e:
            self.logger.error(f"Error collecting hooks: {str(e)}")
            return hooks

    def _find_component_hooks(self, content: str, start_pos: int) -> List[str]:
        """Find hooks used within a component scope safely."""
        try:
            # Find component body
            content_slice = content[start_pos:]
            open_braces = 0
            close_pos = start_pos
            
            for i, char in enumerate(content_slice):
                if char == '{':
                    open_braces += 1
                elif char == '}':
                    open_braces -= 1
                    if open_braces == 0:
                        close_pos = start_pos + i
                        break
            
            component_content = content[start_pos:close_pos]
            return [hook['name'] for hook in self._collect_hooks(component_content)]
            
        except Exception as e:
            self.logger.error(f"Error finding component hooks: {str(e)}")
            return []

    def clean_content(self, content: str) -> str:
        """Clean React/JSX content safely."""
        try:
            # Remove comments safely
            content = re.sub(r'//[^\n]*', '', content)  # Remove single-line comments
            content = re.sub(r'/\*[\s\S]*?\*/', '', content)  # Remove multi-line comments
            content = re.sub(r'{\s*/\*[\s\S]*?\*/\s*}', '', content)  # Remove JSX comments
            
            # Remove empty lines and normalize whitespace
            lines = [line.strip() for line in content.splitlines()]
            return '\n'.join(line for line in lines if line)
            
        except Exception as e:
            self.logger.error(f"Error cleaning content: {str(e)}")
            return content