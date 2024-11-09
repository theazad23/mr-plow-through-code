import re
from typing import Dict, Any, List
from .base_handler import BaseCodeHandler, CodeMetrics
from ..constants import AnalysisKeys as Keys

class JavaHandler(BaseCodeHandler):
    """Handler for Java source code analysis."""
    
    def __init__(self):
        super().__init__()
        self.single_line_comment = '//'
        self.multi_line_comment_start = '/*'
        self.multi_line_comment_end = '*/'
        
    def analyze_code(self, content: str) -> Dict[str, Any]:
        try:
            cleaned = self.clean_content(content)
            metrics = self.count_lines(content)
            metrics.complexity = self._calculate_java_complexity(cleaned)
            metrics.max_depth = self.calculate_max_depth(cleaned)
            
            return {
                Keys.SUCCESS: True,
                Keys.METRICS: Keys.metrics_result(metrics),
                Keys.IMPORTS: self._collect_imports(content),
                Keys.PACKAGES: self._collect_packages(content),
                Keys.FUNCTIONS: self._collect_methods(cleaned),
                Keys.CLASSES: self._collect_classes(cleaned)
            }
        except Exception as e:
            return {Keys.SUCCESS: False, Keys.ERROR: str(e)}
    
    def _calculate_java_complexity(self, content: str) -> int:
        """Calculate cyclomatic complexity for Java code."""
        complexity = 0
        
        # Control structures
        control_patterns = [
            r'\bif\s*\(',           # if statements
            r'\belse\s+if\s*\(',    # else if statements
            r'\bfor\s*\(',          # for loops
            r'\bwhile\s*\(',        # while loops
            r'\bcase\s+[^:]+:',     # case statements
            r'\bcatch\s*\(',        # catch blocks
            r'\b\|\|',              # logical OR
            r'\b&&',                # logical AND
            r'\?',                  # ternary operators
            r'@Override\b'          # method overrides (adds complexity)
        ]
        
        for pattern in control_patterns:
            complexity += len(re.findall(pattern, content))
            
        return max(1, complexity)
    
    def _collect_imports(self, content: str) -> List[str]:
        """Collect all import statements."""
        imports = re.findall(
            r'import\s+(?:static\s+)?([^;]+);',
            content
        )
        return [imp.strip() for imp in imports]
    
    def _collect_packages(self, content: str) -> List[str]:
        """Collect package declarations."""
        packages = re.findall(
            r'package\s+([^;]+);',
            content
        )
        return [pkg.strip() for pkg in packages]
    
    def _collect_methods(self, content: str) -> List[Dict[str, Any]]:
        """Collect method declarations."""
        methods = []
        
        # Match method declarations with various modifiers and annotations
        method_pattern = (
            r'(?:@\w+\s*(?:\([^)]*\))?\s*)*'  # annotations
            r'(?:public|private|protected|static|\s) +'  # modifiers
            r'(?:[\w\<\>\[\]]+\s+)*'  # return type
            r'(\w+)\s*\((.*?)\)'  # method name and parameters
        )
        
        for match in re.finditer(method_pattern, content):
            name = match.group(1)
            if name not in ('if', 'for', 'while', 'switch', 'catch'):  # Skip control structures
                params = self._parse_parameters(match.group(2))
                methods.append(Keys.function_info(
                    name=name,
                    args=params,
                    decorators=self._get_annotations(match.group(0))
                ))
                
        return methods
    
    def _collect_classes(self, content: str) -> List[Dict[str, Any]]:
        """Collect class declarations and their methods."""
        classes = []
        
        # Match class declarations with inheritance and interfaces
        class_pattern = (
            r'(?:@\w+\s*(?:\([^)]*\))?\s*)*'  # annotations
            r'(?:public|private|protected|static|\s)*\s+'  # modifiers
            r'class\s+(\w+)'  # class name
            r'(?:\s+extends\s+(\w+))?'  # optional inheritance
            r'(?:\s+implements\s+([^{]+))?'  # optional interfaces
            r'\s*\{([^}]+)\}'  # class body
        )
        
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            class_body = match.group(4)
            
            # Get base classes (inheritance + interfaces)
            bases = []
            if match.group(2):  # Extended class
                bases.append(match.group(2))
            if match.group(3):  # Implemented interfaces
                bases.extend(intf.strip() for intf in match.group(3).split(','))
            
            # Get methods from class body
            methods = self._collect_methods(class_body)
            
            classes.append(Keys.class_info(
                name=class_name,
                methods=methods,
                bases=bases
            ))
            
        return classes
    
    def _parse_parameters(self, params_str: str) -> List[str]:
        """Parse Java method parameters."""
        if not params_str.strip():
            return []
            
        params = []
        # Split by comma but handle generics properly
        depth = 0
        current = []
        
        for char in params_str:
            if char == '<':
                depth += 1
            elif char == '>':
                depth -= 1
            elif char == ',' and depth == 0:
                params.append(''.join(current).strip())
                current = []
                continue
            current.append(char)
            
        if current:
            params.append(''.join(current).strip())
            
        # Extract parameter names (ignore type information)
        return [param.split()[-1].strip() for param in params]
    
    def _get_annotations(self, method_decl: str) -> List[str]:
        """Extract annotations from method declaration."""
        return re.findall(r'@(\w+)(?:\([^)]*\))?', method_decl)
    
    def clean_content(self, content: str) -> str:
        return self.clean_basic_comments(content)