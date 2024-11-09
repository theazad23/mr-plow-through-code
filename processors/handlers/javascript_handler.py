from typing import Dict, Any, List, Optional
import re
import logging
from .base_handler import BaseCodeHandler, CodeMetrics
from ..constants import AnalysisKeys as Keys

class JavaScriptHandler(BaseCodeHandler):
    """Handler for JavaScript source code analysis with improved regex handling."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.single_line_comment = '//'
        self.multi_line_comment_start = '/*'
        self.multi_line_comment_end = '*/'

    def analyze_code(self, content: str) -> Dict[str, Any]:
        """Analyze JavaScript code with safe regex patterns."""
        try:
            # First clean the content
            cleaned = self.clean_content(content)
            
            # Get basic metrics
            metrics = self.count_lines(content)
            metrics.complexity = self._calculate_complexity(cleaned)
            metrics.max_depth = self._calculate_depth(cleaned)

            return {
                Keys.SUCCESS: True,
                Keys.METRICS: Keys.metrics_result(metrics),
                Keys.IMPORTS: self._collect_imports(cleaned),
                Keys.EXPORTS: self._collect_exports(cleaned),
                Keys.FUNCTIONS: self._collect_functions(cleaned),
                Keys.CLASSES: self._collect_classes(cleaned)
            }
        except Exception as e:
            self.logger.error(f"Error analyzing JavaScript code: {str(e)}")
            return {Keys.SUCCESS: False, Keys.ERROR: str(e)}

    def _calculate_complexity(self, content: str) -> int:
        """Calculate cyclomatic complexity safely."""
        try:
            complexity = 1  # Base complexity

            # Safe patterns for complexity calculation
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
            ]

            for pattern in patterns:
                try:
                    complexity += len(re.findall(pattern, content))
                except Exception:
                    continue

            return max(1, complexity)
        except Exception as e:
            self.logger.error(f"Error calculating complexity: {str(e)}")
            return 1

    def _calculate_depth(self, content: str) -> int:
        """Calculate nesting depth safely."""
        try:
            max_depth = 0
            current_depth = 0
            
            for char in content:
                if char == '{':
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                elif char == '}':
                    current_depth = max(0, current_depth - 1)
            
            return max_depth
        except Exception as e:
            self.logger.error(f"Error calculating depth: {str(e)}")
            return 0

    def _collect_imports(self, content: str) -> List[str]:
        """Collect imports safely."""
        imports = set()
        try:
            # ES6 imports
            import_patterns = [
                r'import\s+(?:{[^}]+}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
                r'import\s+[\'"]([^\'"]+)[\'"]',
                # CommonJS require
                r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
            ]
            
            for pattern in import_patterns:
                try:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        imports.add(match.group(1))
                except Exception:
                    continue

            return sorted(list(imports))
        except Exception as e:
            self.logger.error(f"Error collecting imports: {str(e)}")
            return list(imports)

    def _collect_exports(self, content: str) -> List[str]:
        """Collect exports safely."""
        exports = set()
        try:
            export_patterns = [
                # ES6 exports
                r'export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)',
                r'export\s+default\s+(\w+)',
                r'export\s+{\s*([^}]+)\s*}',
                # CommonJS exports
                r'module\.exports\s*=\s*(\w+)',
                r'exports\.(\w+)\s*='
            ]

            for pattern in export_patterns:
                try:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        exports.add(match.group(1).strip())
                except Exception:
                    continue

            return sorted(list(exports))
        except Exception as e:
            self.logger.error(f"Error collecting exports: {str(e)}")
            return list(exports)

    def _collect_functions(self, content: str) -> List[Dict[str, Any]]:
        """Collect function declarations safely."""
        functions = []
        try:
            # Function patterns
            patterns = [
                # Regular functions
                (r'function\s+(\w+)\s*\((.*?)\)', False),
                # Arrow functions
                (r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\((.*?)\)\s*=>', True),
                # Method definitions
                (r'(?:async\s+)?(\w+)\s*\((.*?)\)\s*{', False)
            ]

            for pattern, is_arrow in patterns:
                try:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        name = match.group(1)
                        params = self._parse_parameters(match.group(2))
                        functions.append(Keys.function_info(
                            name=name,
                            args=params,
                            is_async='async' in content[match.start()-5:match.start()]
                        ))
                except Exception:
                    continue

            return functions
        except Exception as e:
            self.logger.error(f"Error collecting functions: {str(e)}")
            return functions

    def _collect_classes(self, content: str) -> List[Dict[str, Any]]:
        """Collect class declarations safely."""
        classes = []
        try:
            # Class pattern
            class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*{'
            
            matches = re.finditer(class_pattern, content)
            for match in matches:
                class_name = match.group(1)
                base_class = match.group(2)
                
                # Find class body
                start_pos = match.end()
                class_body = self._extract_block_content(content[start_pos:])
                
                methods = self._collect_methods(class_body)
                
                classes.append(Keys.class_info(
                    name=class_name,
                    methods=methods,
                    bases=[base_class] if base_class else []
                ))

            return classes
        except Exception as e:
            self.logger.error(f"Error collecting classes: {str(e)}")
            return classes

    def _collect_methods(self, class_body: str) -> List[Dict[str, Any]]:
        """Collect class methods safely."""
        methods = []
        try:
            method_pattern = r'(?:async\s+)?(?:static\s+)?(\w+)\s*\((.*?)\)\s*{'
            
            matches = re.finditer(method_pattern, class_body)
            for match in matches:
                name = match.group(1)
                if name not in ('if', 'for', 'while', 'switch'):
                    methods.append(Keys.function_info(
                        name=name,
                        args=self._parse_parameters(match.group(2)),
                        is_async='async' in class_body[match.start()-5:match.start()]
                    ))

            return methods
        except Exception as e:
            self.logger.error(f"Error collecting methods: {str(e)}")
            return methods

    def _parse_parameters(self, params_str: str) -> List[str]:
        """Parse function parameters safely."""
        try:
            if not params_str.strip():
                return []
            
            # Split by comma but respect nested structures
            params = []
            current_param = []
            nesting_level = 0
            
            for char in params_str:
                if char in '{([':
                    nesting_level += 1
                elif char in '})]':
                    nesting_level -= 1
                elif char == ',' and nesting_level == 0:
                    params.append(''.join(current_param).strip())
                    current_param = []
                    continue
                current_param.append(char)
            
            if current_param:
                params.append(''.join(current_param).strip())
            
            # Clean up parameter names
            cleaned_params = []
            for param in params:
                # Remove default values and type annotations
                base_param = param.split('=')[0].split(':')[0].strip()
                if base_param:
                    cleaned_params.append(base_param)
            
            return cleaned_params
        except Exception as e:
            self.logger.error(f"Error parsing parameters: {str(e)}")
            return []

    def _extract_block_content(self, content: str) -> str:
        """Extract content between matching braces safely."""
        try:
            nesting_level = 1
            for i, char in enumerate(content):
                if char == '{':
                    nesting_level += 1
                elif char == '}':
                    nesting_level -= 1
                    if nesting_level == 0:
                        return content[:i]
            return content
        except Exception as e:
            self.logger.error(f"Error extracting block content: {str(e)}")
            return ""

    def clean_content(self, content: str) -> str:
        """Clean JavaScript content safely."""
        try:
            # Remove comments safely
            content = re.sub(r'//[^\n]*', '', content)  # Remove single-line comments
            content = re.sub(r'/\*[\s\S]*?\*/', '', content)  # Remove multi-line comments
            
            # Remove empty lines and normalize whitespace
            lines = [line.strip() for line in content.splitlines()]
            return '\n'.join(line for line in lines if line)
        except Exception as e:
            self.logger.error(f"Error cleaning content: {str(e)}")
            return content