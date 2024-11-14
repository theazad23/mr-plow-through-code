# src/handlers/plugins/javascript.py
from typing import Dict, Any, List
import re
from ..base import BaseHandler, BaseParserMixin, LanguageConfig, CodeMetrics

class JavaScriptHandler(BaseHandler, BaseParserMixin):
    """Handler for JavaScript/TypeScript source code analysis."""
    
    config = LanguageConfig(
        name="javascript",
        file_extensions={'.js', '.jsx', '.ts', '.tsx'},
        single_line_comment='//',
        multi_line_comment_start='/*',
        multi_line_comment_end='*/',
        test_file_patterns={
            r'test_.*\.(js|ts)x?$',
            r'.*\.test\.(js|ts)x?$',
            r'.*\.spec\.(js|ts)x?$',
            r'__tests__/.*\.(js|ts)x?$'
        },
        keywords={
            'function', 'class', 'if', 'else', 'for', 'while', 'switch',
            'case', 'try', 'catch', 'const', 'let', 'var', 'import',
            'export', 'default', 'return', 'async', 'await'
        },
        complexity_patterns={
            r'\bif\b', r'\belse\s+if\b', r'\bfor\b', r'\bwhile\b',
            r'\bswitch\b', r'\bcatch\b', r'\?', r'&&', r'\|\|',
            r'\.map\b', r'\.filter\b', r'\.reduce\b'
        }
    )

    def analyze_code(self, content: str) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript code content."""
        try:
            cleaned = self.clean_content(content)
            metrics = self._calculate_metrics(cleaned)
            
            analysis = {
                'success': True,
                'metrics': {
                    'lines_of_code': metrics.lines_of_code,
                    'comment_lines': metrics.comment_lines,
                    'blank_lines': metrics.blank_lines,
                    'complexity': metrics.complexity,
                    'maintainability_index': metrics.maintainability_index,
                    'max_depth': metrics.max_depth
                },
                'imports': self.parse_imports(cleaned),
                'exports': self.parse_exports(cleaned),
                'functions': self.parse_functions(cleaned),
                'classes': self.parse_classes(cleaned)
            }
            
            # Add React-specific analysis if detected
            if self._is_react_code(cleaned):
                analysis.update({
                    'is_react': True,
                    'components': self._parse_react_components(cleaned),
                    'hooks': self._parse_react_hooks(cleaned)
                })
            
            return analysis
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def clean_content(self, content: str) -> str:
        """Clean JavaScript/TypeScript content."""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        content = re.sub(r'/\*[\s\S]*?\*/', '', content)
        
        # Normalize whitespace
        lines = [line.strip() for line in content.splitlines()]
        return '\n'.join(line for line in lines if line)

    def _calculate_metrics(self, content: str) -> CodeMetrics:
        """Calculate code metrics."""
        metrics = CodeMetrics()
        lines = content.splitlines()
        metrics.lines_of_code = len(lines)
        metrics.blank_lines = sum(1 for line in lines if not line.strip())
        
        # Calculate complexity
        complexity = 1
        for pattern in self.config.complexity_patterns:
            complexity += len(re.findall(pattern, content))
        metrics.complexity = complexity

        # Calculate max depth
        current_depth = 0
        max_depth = 0
        jsx_depth = 0
        
        for line in lines:
            # Track JSX depth
            jsx_open = len(re.findall(r'<[A-Z]\w+', line))
            jsx_close = len(re.findall(r'</[A-Z]\w+', line)) + line.count('/>')
            jsx_depth += jsx_open - jsx_close
            
            # Track code block depth
            current_depth += line.count('{') - line.count('}')
            max_depth = max(max_depth, current_depth, jsx_depth)
            
        metrics.max_depth = max_depth
        return metrics

    def parse_functions(self, content: str) -> List[Dict[str, Any]]:
        """Parse function declarations."""
        functions = []
        patterns = [
            (r'function\s+([\w$]+)\s*\((.*?)\)', False),  # Named functions
            (r'([\w$]+)\s*=\s*function\s*\((.*?)\)', False),  # Function expressions
            (r'([\w$]+)\s*=\s*\((.*?)\)\s*=>', True),  # Arrow functions
            (r'async\s+function\s+([\w$]+)\s*\((.*?)\)', True)  # Async functions
        ]

        for pattern, is_arrow in patterns:
            for match in re.finditer(pattern, content):
                name = match.group(1)
                params = self._parse_parameters(match.group(2))
                functions.append({
                    'name': name,
                    'parameters': params,
                    'is_async': is_arrow or 'async' in content[match.start()-5:match.start()]
                })

        return functions

    def parse_classes(self, content: str) -> List[Dict[str, Any]]:
        """Parse class declarations."""
        classes = []
        class_pattern = r'class\s+([\w$]+)(?:\s+extends\s+([\w$.]+))?\s*{([^}]+)}'
        
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            base_class = match.group(2)
            class_body = match.group(3)
            
            methods = self._parse_class_methods(class_body)
            classes.append({
                'name': class_name,
                'methods': methods,
                'extends': base_class if base_class else None
            })

        return classes

    def parse_imports(self, content: str) -> List[str]:
        """Parse import statements."""
        imports = set()
        patterns = [
            r'import\s+(?:{[^}]+}|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'import\s+[\'"]([^\'"]+)[\'"]',
            r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                imports.add(match.group(1))

        return sorted(list(imports))

    def parse_exports(self, content: str) -> List[Dict[str, Any]]:
        """Parse export statements."""
        exports = []
        patterns = [
            (r'export\s+(?:default\s+)?(?:function|class|const|let|var)\s+([\w$]+)', 'named'),
            (r'export\s+default\s+([\w$]+)', 'default'),
            (r'export\s+{\s*([^}]+)\s*}', 'grouped'),
            (r'module\.exports\s*=\s*([\w$]+)', 'commonjs'),
            (r'exports\.([\w$]+)\s*=', 'commonjs-property')
        ]

        for pattern, export_type in patterns:
            for match in re.finditer(pattern, content):
                if export_type == 'grouped':
                    for name in match.group(1).split(','):
                        clean_name = name.strip().split(' as ')[0]
                        exports.append({
                            'name': clean_name,
                            'type': 'named'
                        })
                else:
                    exports.append({
                        'name': match.group(1),
                        'type': export_type
                    })

        return exports

    def _is_react_code(self, content: str) -> bool:
        """Detect if the code contains React patterns."""
        react_patterns = [
            r'import\s+.*?[\'"]react[\'"]',
            r'import\s+{[^}]*Component[^}]*}\s+from\s+[\'"]react[\'"]',
            r'extends\s+React\.Component',
            r'extends\s+Component',
            r'use[A-Z]\w+\(',  # Hook pattern
            r'<[\w]+\s+[^>]*/>',  # JSX pattern
            r'React\.'
        ]
        return any(re.search(pattern, content) for pattern in react_patterns)

    def _parse_react_components(self, content: str) -> List[Dict[str, Any]]:
        """Parse React component declarations."""
        components = []
        patterns = [
            (r'(?:export\s+)?(?:default\s+)?function\s+([A-Z][\w$]*)\s*\((.*?)\)', 'function'),
            (r'(?:export\s+)?(?:default\s+)?const\s+([A-Z][\w$]*)\s*=\s*(?:\((.*?)\))?\s*=>', 'arrow'),
            (r'class\s+([A-Z][\w$]*)\s+extends\s+(?:React\.)?Component', 'class')
        ]

        for pattern, comp_type in patterns:
            for match in re.finditer(pattern, content):
                name = match.group(1)
                props = []
                if comp_type != 'class' and match.group(2):
                    props = self._parse_parameters(match.group(2))
                    
                hooks = self._find_component_hooks(content, match.end())
                components.append({
                    'name': name,
                    'type': comp_type,
                    'props': props,
                    'hooks': hooks,
                    'lifecycle_methods': self._find_lifecycle_methods(content, match.end()) if comp_type == 'class' else []
                })

        return components

    def _parse_react_hooks(self, content: str) -> List[Dict[str, Any]]:
        """Parse React hook usage."""
        hooks = []
        standard_hooks = {
            'useState', 'useEffect', 'useContext', 'useReducer',
            'useCallback', 'useMemo', 'useRef', 'useImperativeHandle',
            'useLayoutEffect', 'useDebugValue'
        }

        hook_pattern = r'\b(use[A-Z]\w+)'
        for match in re.finditer(hook_pattern, content):
            hook_name = match.group(1)
            if hook_name.startswith('use'):
                hooks.append({
                    'name': hook_name,
                    'is_custom': hook_name not in standard_hooks,
                    'dependencies': self._parse_hook_dependencies(content, match.end())
                })

        return hooks

    def _parse_parameters(self, params_str: str) -> List[str]:
        """Parse function parameters."""
        if not params_str.strip():
            return []
        
        params = []
        current_param = []
        depth = 0
        
        for char in params_str:
            if char in '{[(':
                depth += 1
            elif char in '}])':
                depth -= 1
            elif char == ',' and depth == 0:
                param = ''.join(current_param).strip()
                if param:
                    params.append(param)
                current_param = []
                continue
            current_param.append(char)
        
        if current_param:
            param = ''.join(current_param).strip()
            if param:
                params.append(param)
        
        # Clean parameters (remove type annotations and default values)
        cleaned_params = []
        for param in params:
            # Remove TypeScript type annotations
            param = re.sub(r':\s*[^=,}]+', '', param)
            # Remove default values
            param = param.split('=')[0].strip()
            # Remove destructuring
            if param.startswith('{'):
                param_match = re.search(r'{([^}]+)}', param)
                if param_match:
                    cleaned_params.extend(p.strip() for p in param_match.group(1).split(','))
                continue
            cleaned_params.append(param)
            
        return cleaned_params

    def _parse_class_methods(self, class_body: str) -> List[Dict[str, Any]]:
        """Parse class methods."""
        methods = []
        method_pattern = r'(?:async\s+)?(?:static\s+)?([\w$]+)\s*\((.*?)\)'
        
        for match in re.finditer(method_pattern, class_body):
            name = match.group(1)
            if name not in ('constructor', 'render'):
                methods.append({
                    'name': name,
                    'parameters': self._parse_parameters(match.group(2)),
                    'is_async': 'async' in class_body[match.start()-5:match.start()]
                })
        
        return methods

    def _find_component_hooks(self, content: str, start_pos: int) -> List[str]:
        """Find hooks used in a component."""
        end_pos = self._find_block_end(content, start_pos)
        if end_pos > start_pos:
            component_content = content[start_pos:end_pos]
            hook_pattern = r'use[A-Z]\w+'
            return list(set(re.findall(hook_pattern, component_content)))
        return []

    def _parse_hook_dependencies(self, content: str, start_pos: int) -> List[str]:
        """Parse hook dependency arrays."""
        deps = []
        # Look for the dependency array after the hook call
        dep_pattern = r'\[[^\]]*\]'
        line_end = content.find('\n', start_pos)
        if line_end == -1:
            line_end = len(content)
        line_content = content[start_pos:line_end]
        
        dep_match = re.search(dep_pattern, line_content)
        if dep_match:
            deps_str = dep_match.group(0)[1:-1]  # Remove brackets
            deps = [dep.strip() for dep in deps_str.split(',') if dep.strip()]
        
        return deps

    def _find_lifecycle_methods(self, content: str, start_pos: int) -> List[str]:
        """Find React lifecycle methods in class components."""
        lifecycle_methods = {
            'componentDidMount', 'componentDidUpdate', 'componentWillUnmount',
            'shouldComponentUpdate', 'getSnapshotBeforeUpdate', 'componentDidCatch',
            'getDerivedStateFromProps', 'getDerivedStateFromError'
        }
        
        end_pos = self._find_block_end(content, start_pos)
        if end_pos > start_pos:
            component_content = content[start_pos:end_pos]
            found_methods = []
            for method in lifecycle_methods:
                if re.search(rf'\b{method}\b', component_content):
                    found_methods.append(method)
            return found_methods
        return []

    def _find_block_end(self, content: str, start_pos: int) -> int:
        """Find the end position of a code block."""
        depth = 0
        pos = start_pos
        
        while pos < len(content):
            char = content[pos]
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return pos
            pos += 1
            
        return start_pos