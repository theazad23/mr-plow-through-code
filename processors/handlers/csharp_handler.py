from typing import Dict, Any, List, Optional
import re
from .base_handler import BaseCodeHandler, CodeMetrics
from ..constants import AnalysisKeys as Keys
import logging

class CSharpHandler(BaseCodeHandler):
    """Handler for C# source code analysis with support for .NET Framework up to .NET 8."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.single_line_comment = '//'
        self.multi_line_comment_start = '/*'
        self.multi_line_comment_end = '*/'
        
    def analyze_code(self, content: str) -> Dict[str, Any]:
        """Analyze C# code content."""
        try:
            cleaned = self.clean_content(content)
            metrics = self.count_lines(content)
            metrics.complexity = self._calculate_complexity(cleaned)
            metrics.max_depth = self._calculate_depth(cleaned)
            
            return {
                Keys.SUCCESS: True,
                Keys.METRICS: Keys.metrics_result(metrics),
                Keys.IMPORTS: self._collect_imports(cleaned),
                Keys.FUNCTIONS: self._collect_methods(cleaned),
                Keys.CLASSES: self._collect_classes(cleaned),
                Keys.DEPENDENCIES: self._collect_dependencies(cleaned),
                'namespace': self._get_namespace(cleaned)
            }
        except Exception as e:
            self.logger.error(f'Error analyzing C# code: {str(e)}')
            return {Keys.SUCCESS: False, Keys.ERROR: str(e)}

    def _calculate_complexity(self, content: str) -> int:
        """Calculate cyclomatic complexity for C# code."""
        try:
            complexity = 1
            patterns = [
                r'\bif\s*\(',
                r'\belse\s+if\b',
                r'\bfor\s*\(',
                r'\bforeach\s*\(',
                r'\bwhile\s*\(',
                r'\bcase\b',
                r'\bcatch\s*\(',
                r'\b\|\|',
                r'\b&&',
                r'\?',
                r'\byield\s+return\b',
                r'\bawait\b',
                r'\block\s*\(',
                r'\bswitch\s*\('
            ]
            
            for pattern in patterns:
                try:
                    complexity += len(re.findall(pattern, content))
                except Exception:
                    continue
                    
            return max(1, complexity)
        except Exception as e:
            self.logger.error(f'Error calculating complexity: {str(e)}')
            return 1

    def _calculate_depth(self, content: str) -> int:
        """Calculate nesting depth for C# code."""
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
            self.logger.error(f'Error calculating depth: {str(e)}')
            return 0

    def _collect_imports(self, content: str) -> List[str]:
        """Collect using statements and references."""
        imports = set()
        try:
            # Match using statements
            using_pattern = r'using\s+([^;]+);'
            matches = re.finditer(using_pattern, content)
            
            for match in matches:
                import_stmt = match.group(1).strip()
                if not import_stmt.startswith('('):  # Exclude using statements in using blocks
                    imports.add(import_stmt)
                    
            return sorted(list(imports))
        except Exception as e:
            self.logger.error(f'Error collecting imports: {str(e)}')
            return list(imports)

    def _collect_dependencies(self, content: str) -> Dict[str, List[str]]:
        """Collect .NET dependencies and target framework information."""
        dependencies = {
            'frameworks': [],
            'packages': []
        }
        
        try:
            # Find target framework declarations
            framework_pattern = r'<TargetFramework[s]?>[^<]+</TargetFramework[s]?>'
            framework_matches = re.finditer(framework_pattern, content)
            for match in framework_matches:
                framework = re.sub(r'<[^>]+>', '', match.group(0))
                dependencies['frameworks'].extend(framework.split(';'))

            # Find package references
            package_pattern = r'<PackageReference\s+Include="([^"]+)"\s+Version="([^"]+)"'
            package_matches = re.finditer(package_pattern, content)
            for match in package_matches:
                package = f"{match.group(1)}@{match.group(2)}"
                dependencies['packages'].append(package)

            return dependencies
        except Exception as e:
            self.logger.error(f'Error collecting dependencies: {str(e)}')
            return dependencies

    def _collect_methods(self, content: str) -> List[Dict[str, Any]]:
        """Collect method declarations."""
        methods = []
        try:
            # Match method declarations including async methods and generics
            method_pattern = r'(?:public|private|protected|internal|static|virtual|override|abstract|async|\s)+(?:<[^>]+>)?\s+(?:[a-zA-Z0-9_<>[\],\s]+)\s+([a-zA-Z0-9_]+)\s*\((.*?)\)'
            matches = re.finditer(method_pattern, content)
            
            for match in matches:
                name = match.group(1)
                if name not in ('if', 'for', 'while', 'switch'):
                    params = self._parse_parameters(match.group(2))
                    is_async = bool(re.search(r'\basync\b', content[match.start():match.end()]))
                    decorators = self._get_attributes(content, match.start())
                    
                    methods.append(Keys.function_info(
                        name=name,
                        args=params,
                        decorators=decorators,
                        is_async=is_async
                    ))
                    
            return methods
        except Exception as e:
            self.logger.error(f'Error collecting methods: {str(e)}')
            return methods

    def _collect_classes(self, content: str) -> List[Dict[str, Any]]:
        """Collect class declarations."""
        classes = []
        try:
            # Match class declarations including generic classes
            class_pattern = r'(?:public|private|protected|internal|static|sealed|abstract|\s)+class\s+([a-zA-Z0-9_]+)(?:<[^>]+>)?(?:\s*:\s*([^{]+))?'
            matches = re.finditer(class_pattern, content)
            
            for match in matches:
                class_name = match.group(1)
                inheritance = match.group(2)
                bases = []
                
                if inheritance:
                    bases = [base.strip() for base in inheritance.split(',')]
                
                # Find class body and collect methods
                start_pos = content.find('{', match.end())
                if start_pos != -1:
                    class_body = self._extract_block_content(content[start_pos:])
                    methods = self._collect_methods(class_body)
                    
                    classes.append(Keys.class_info(
                        name=class_name,
                        methods=methods,
                        bases=bases
                    ))
                    
            return classes
        except Exception as e:
            self.logger.error(f'Error collecting classes: {str(e)}')
            return classes

    def _get_namespace(self, content: str) -> Optional[str]:
        """Extract namespace information."""
        try:
            # Support both traditional and file-scoped namespaces
            traditional = re.search(r'namespace\s+([^{\s;]+)', content)
            file_scoped = re.search(r'namespace\s+([^;\s]+);', content)
            
            if traditional:
                return traditional.group(1)
            elif file_scoped:
                return file_scoped.group(1)
            return None
        except Exception as e:
            self.logger.error(f'Error getting namespace: {str(e)}')
            return None

    def _parse_parameters(self, params_str: str) -> List[str]:
        """Parse method parameters."""
        try:
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
                    params.append(''.join(current_param).strip())
                    current_param = []
                    continue
                current_param.append(char)
                
            if current_param:
                params.append(''.join(current_param).strip())
                
            # Clean parameters to just parameter names
            cleaned_params = []
            for param in params:
                # Remove attributes
                param = re.sub(r'\[[^\]]+\]', '', param)
                # Get just the parameter name
                param_parts = param.split()
                if param_parts:
                    cleaned_params.append(param_parts[-1].strip())
                    
            return cleaned_params
        except Exception as e:
            self.logger.error(f'Error parsing parameters: {str(e)}')
            return []

    def _get_attributes(self, content: str, position: int) -> List[str]:
        """Extract C# attributes (decorators)."""
        try:
            # Look for attributes before the given position
            code_before = content[:position]
            last_newline = code_before.rfind('\n')
            relevant_code = code_before[last_newline + 1:]
            
            attributes = []
            attribute_pattern = r'\[([^\]]+)\]'
            matches = re.finditer(attribute_pattern, relevant_code)
            
            for match in matches:
                attr = match.group(1)
                if '(' in attr:
                    attr = attr[:attr.find('(')]
                attributes.append(attr.strip())
                
            return attributes
        except Exception as e:
            self.logger.error(f'Error getting attributes: {str(e)}')
            return []

    def _extract_block_content(self, content: str) -> str:
        """Extract content between matching braces."""
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
            self.logger.error(f'Error extracting block content: {str(e)}')
            return ''

    def clean_content(self, content: str) -> str:
        """Clean C# content by removing comments and unnecessary whitespace."""
        try:
            # Remove single-line comments
            content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
            # Remove multi-line comments
            content = re.sub(r'/\*[\s\S]*?\*/', '', content)
            # Normalize whitespace
            lines = [line.strip() for line in content.splitlines()]
            return '\n'.join(line for line in lines if line)
        except Exception as e:
            self.logger.error(f'Error cleaning content: {str(e)}')
            return content