from typing import Dict, Any, List, Optional
import re
import logging
from .base_handler import BaseCodeHandler, CodeMetrics
from ..constants import AnalysisKeys as Keys

class JavaScriptHandler(BaseCodeHandler):
    """
    Unified handler for JavaScript, TypeScript, React and Node.js code analysis.
    Supports .js, .jsx, .ts, and .tsx files.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.single_line_comment = '//'
        self.multi_line_comment_start = '/*'
        self.multi_line_comment_end = '*/'
        
    def analyze_code(self, content: str) -> Dict[str, Any]:
        try:
            cleaned = self.clean_content(content)
            metrics = self.count_lines(content)
            metrics.complexity = self._calculate_complexity(cleaned)
            metrics.max_depth = self._calculate_depth(cleaned)
            
            analysis = {
                Keys.SUCCESS: True,
                Keys.METRICS: Keys.metrics_result(metrics),
                Keys.IMPORTS: self._collect_imports(cleaned),
                Keys.EXPORTS: self._collect_exports(cleaned),
                Keys.FUNCTIONS: self.collect_functions(cleaned),
                Keys.CLASSES: self.collect_classes(cleaned)
            }
            
            # Add React-specific analysis if React patterns are detected
            if self._is_react_code(cleaned):
                analysis.update({
                    Keys.COMPONENTS: self._collect_components(cleaned),
                    Keys.HOOKS: self._collect_hooks(cleaned),
                })
            
            return analysis
        except Exception as e:
            self.logger.error(f"Error analyzing JavaScript/React code: {str(e)}")
            return {Keys.SUCCESS: False, Keys.ERROR: str(e)}

    def _is_react_code(self, content: str) -> bool:
        """Detect if the code contains React patterns."""
        react_patterns = [
            r'import\s+.*?[\'"](react|react-dom)[\'"]',
            r'import\s+{[^}]*Component[^}]*}\s+from\s+[\'"]react[\'"]',
            r'extends\s+React\.Component',
            r'extends\s+Component',
            r'use[A-Z]\w+\(',  # Hook pattern
            r'<[\w]+\s+[^>]*/>',  # JSX pattern
            r'React\.'
        ]
        return any(re.search(pattern, content) for pattern in react_patterns)

    def _calculate_complexity(self, content: str) -> int:
        try:
            complexity = 1
            patterns = [
                # Control flow patterns
                r'\bif\s*\(',
                r'\belse\s+if\b',
                r'\bfor\s*\(',
                r'\bwhile\s*\(',
                r'\bswitch\s*\(',
                r'\bcatch\s*\(',
                # Logical patterns
                r'\?\s*[^:]+\s*:\s*[^;]+',  # Ternary
                r'&&',
                r'\|\|',
                # React-specific patterns
                r'\.map\(',
                r'\.filter\(',
                r'\.reduce\(',
                r'\buseEffect\(',
                r'\buseCallback\(',
                r'\buseMemo\(',
                # Async patterns
                r'\basync\b',
                r'\bawait\b',
                # JSX conditional rendering
                r'{\s*?.+?\s*?\?',
                r'{\s*?!!'
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
        try:
            max_depth = 0
            current_depth = 0
            jsx_depth = 0
            
            lines = content.splitlines()
            for line in lines:
                # Track JSX depth
                jsx_open = len(re.findall(r'<[A-Z]\w+', line))
                jsx_close = len(re.findall(r'</[A-Z]\w+', line)) + line.count('/>')
                jsx_depth += jsx_open - jsx_close
                
                # Track code block depth
                current_depth += line.count('{') - line.count('}')
                
                # Use the maximum of JSX and code block depth
                max_depth = max(max_depth, current_depth, jsx_depth)
            
            return max_depth
        except Exception as e:
            self.logger.error(f"Error calculating depth: {str(e)}")
            return 0

    def _collect_imports(self, content: str) -> List[str]:
        imports = set()
        try:
            patterns = [
                # ES6 imports
                r'import\s+(?:{[^}]+}|\w+)\s+from\s+[\'"]([@\w\-/.]+)[\'"]',
                r'import\s+[\'"]([@\w\-/.]+)[\'"]',
                # CommonJS requires
                r'require\s*\(\s*[\'"]([@\w\-/.]+)[\'"]\s*\)',
                # Dynamic imports
                r'import\s*\(\s*[\'"]([@\w\-/.]+)[\'"]\s*\)'
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    imports.add(match.group(1))
                    
            return sorted(list(imports))
        except Exception as e:
            self.logger.error(f"Error collecting imports: {str(e)}")
            return list(imports)

    def _collect_exports(self, content: str) -> List[str]:
        exports = set()
        try:
            patterns = [
                r'export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)',
                r'export\s+default\s+(\w+)',
                r'export\s+{\s*([^}]+)\s*}',
                r'module\.exports\s*=\s*(\w+)',
                r'exports\.(\w+)\s*='
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    export_items = match.group(1).split(',')
                    for item in export_items:
                        # Clean up the export name
                        clean_name = re.sub(r'\s+as\s+\w+', '', item.strip())
                        if clean_name:
                            exports.add(clean_name)
                            
            return sorted(list(exports))
        except Exception as e:
            self.logger.error(f"Error collecting exports: {str(e)}")
            return list(exports)

    def _collect_components(self, content: str) -> List[Dict[str, Any]]:
        components = []
        try:
            patterns = [
                # Function components
                (r'(?:export\s+)?(?:default\s+)?function\s+([A-Z]\w+)', 'function'),
                # Arrow function components
                (r'(?:export\s+)?(?:default\s+)?const\s+([A-Z]\w+)\s*=\s*(?:\([^)]*\))?\s*=>', 'arrow'),
                # Class components
                (r'class\s+([A-Z]\w+)\s+extends\s+(?:React\.)?Component', 'class')
            ]
            
            for pattern, comp_type in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    name = match.group(1)
                    component_info = {
                        'name': name,
                        'type': comp_type,
                        'hooks': self._find_component_hooks(content, match.start()) if comp_type != 'class' else [],
                        'props': self._extract_props(content, match.start())
                    }
                    components.append(component_info)
                    
            return components
        except Exception as e:
            self.logger.error(f"Error collecting components: {str(e)}")
            return components

    def _collect_hooks(self, content: str) -> List[Dict[str, Any]]:
        hooks = []
        try:
            # Find all hook declarations
            hook_pattern = r'\b(use[A-Z]\w+)'
            
            # Standard React hooks
            standard_hooks = {
                'useState', 'useEffect', 'useContext', 'useReducer',
                'useCallback', 'useMemo', 'useRef', 'useImperativeHandle',
                'useLayoutEffect', 'useDebugValue'
            }
            
            matches = re.finditer(hook_pattern, content)
            for match in matches:
                hook_name = match.group(1)
                if hook_name.startswith('use'):
                    hooks.append({
                        'name': hook_name,
                        'custom': hook_name not in standard_hooks,
                        'dependencies': self._extract_hook_dependencies(content, match.end())
                    })
                    
            return hooks
        except Exception as e:
            self.logger.error(f"Error collecting hooks: {str(e)}")
            return hooks

    def _extract_props(self, content: str, start_pos: int) -> List[str]:
        props = set()
        try:
            # Look for destructured props in parameter list
            param_pattern = r'\(\s*{\s*([^}]+)\s*}\s*\)'
            param_match = re.search(param_pattern, content[start_pos:start_pos + 200])
            if param_match:
                props.update(p.strip() for p in param_match.group(1).split(','))
            
            # Look for props usage in the component body
            props_pattern = r'props\.(\w+)'
            props.update(match.group(1) for match in re.finditer(props_pattern, content[start_pos:]))
            
            return sorted(list(props))
        except Exception as e:
            self.logger.error(f"Error extracting props: {str(e)}")
            return list(props)

    def _extract_hook_dependencies(self, content: str, start_pos: int) -> List[str]:
        try:
            # Find the closing parenthesis of the hook call
            bracket_count = 1
            end_pos = start_pos
            in_array = False
            array_content = []
            
            while bracket_count > 0 and end_pos < len(content):
                char = content[end_pos]
                if char == '[':
                    in_array = True
                elif char == ']' and in_array:
                    break
                elif in_array:
                    array_content.append(char)
                end_pos += 1
                
            if array_content:
                # Parse the dependency array content
                deps = ''.join(array_content).split(',')
                return [dep.strip() for dep in deps if dep.strip()]
            return []
        except Exception as e:
            self.logger.error(f"Error extracting hook dependencies: {str(e)}")
            return []

    def _find_component_hooks(self, content: str, start_pos: int) -> List[str]:
        try:
            # Find the component's closing brace
            bracket_count = 0
            in_component = False
            component_content = []
            
            for pos in range(start_pos, len(content)):
                char = content[pos]
                if char == '{':
                    bracket_count += 1
                    in_component = True
                elif char == '}':
                    bracket_count -= 1
                    if bracket_count == 0 and in_component:
                        break
                elif in_component:
                    component_content.append(char)
                    
            component_str = ''.join(component_content)
            return [hook['name'] for hook in self._collect_hooks(component_str)]
        except Exception as e:
            self.logger.error(f"Error finding component hooks: {str(e)}")
            return []

    def clean_content(self, content: str) -> str:
        try:
            # Remove single-line comments
            content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
            # Remove multi-line comments
            content = re.sub(r'/\*[\s\S]*?\*/', '', content)
            # Remove empty lines and trim
            lines = [line.strip() for line in content.splitlines()]
            return '\n'.join(line for line in lines if line)
        except Exception as e:
            self.logger.error(f"Error cleaning content: {str(e)}")
            return content
        
    def collect_functions(self, content: str) -> List[Dict[str, Any]]:
        functions = []
        try:
            patterns = [
                # Regular functions
                (r'function\s+([\w$]+)\s*\((.*?)\)', False),
                # Arrow functions with name
                (r'(?:const|let|var)\s+([\w$]+)\s*=\s*(?:async\s*)?(?:\((.*?)\)|[\w$]+)\s*=>', True),
                # Object method shorthand
                (r'(?:async\s+)?([\w$]+)\s*\((.*?)\)\s*{', False)
            ]
            
            for pattern, is_arrow in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    name = match.group(1)
                    params = self._parse_parameters(match.group(2) if match.group(2) else '')
                    
                    functions.append(Keys.function_info(
                        name=name,
                        args=params,
                        is_async='async' in content[match.start()-5:match.start()]
                    ))
                    
            return functions
        except Exception as e:
            self.logger.error(f"Error collecting functions: {str(e)}")
            return functions

    def collect_classes(self, content: str) -> List[Dict[str, Any]]:
        classes = []
        try:
            # Match class declarations
            class_pattern = r'class\s+([\w$]+)(?:\s+extends\s+([\w$.]+))?\s*{([^}]+)}'
            matches = re.finditer(class_pattern, content)
            
            for match in matches:
                class_name = match.group(1)
                base_class = match.group(2)
                class_body = match.group(3)
                
                # Collect methods from class body
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
    def _parse_parameters(self, params_str: str) -> List[str]:
        try:
            if not params_str.strip():
                return []
                
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
                # Remove type annotations and default values
                base_param = param.split('=')[0].split(':')[0].strip()
                if base_param:
                    cleaned_params.append(base_param)
                    
            return cleaned_params
        except Exception as e:
            self.logger.error(f"Error parsing parameters: {str(e)}")
            return []

    def _collect_methods(self, class_body: str) -> List[Dict[str, Any]]:
        methods = []
        try:
            # Match both regular and class methods
            method_pattern = r'(?:async\s+)?(?:static\s+)?([\w$]+)\s*\((.*?)\)\s*{[^}]*}'
            matches = re.finditer(method_pattern, class_body)
            
            for match in matches:
                name = match.group(1)
                # Skip if name is a control structure keyword
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