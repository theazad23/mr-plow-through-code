from typing import Dict, Any, List
import re
from ..base import BaseHandler, BaseParserMixin, LanguageConfig, CodeMetrics

class CSharpHandler(BaseHandler, BaseParserMixin):
    """Handler for C# source code analysis with support for .NET Framework and .NET Core."""
    
    config = LanguageConfig(
        name="csharp",
        file_extensions={
            '.cs',          # C# source files
            '.cshtml',      # Razor views
            '.razor',       # Blazor components
            '.csx',         # C# scripts
            '.vb',          # Visual Basic .NET
            '.fs',          # F#
            '.fsx',         # F# scripts
            '.xaml',        # XAML files
            '.aspx',        # ASP.NET Web Forms
            '.ascx',        # ASP.NET User Controls
            '.master'       # ASP.NET Master Pages
        },
        single_line_comment='//',
        multi_line_comment_start='/*',
        multi_line_comment_end='*/',
        test_file_patterns={
            r'.*Tests?\.cs$',
            r'.*Spec\.cs$',
            r'.*\.Test\.cs$',
            r'.*\.Tests\.cs$',
            r'.*\.Specs\.cs$',
            r'test/.*\.cs$',
            r'tests/.*\.cs$'
        },
        keywords={
            'class', 'interface', 'struct', 'enum', 'namespace',
            'public', 'private', 'protected', 'internal', 'static',
            'virtual', 'override', 'abstract', 'sealed', 'async',
            'await', 'using', 'partial', 'get', 'set'
        },
        complexity_patterns={
            r'\bif\b', r'\belse\s+if\b', r'\bfor\b', r'\bforeach\b',
            r'\bwhile\b', r'\bcase\b', r'\bcatch\b', r'\?\?', r'\?\.', 
            r'&&', r'\|\|', r'\byield\s+return\b', r'\bawait\b',
            r'\block\s*\(', r'\bswitch\b'
        }
    )

    def analyze_code(self, content: str) -> Dict[str, Any]:
        """Analyze C# code content."""
        try:
            cleaned = self.clean_content(content)
            metrics = self._calculate_metrics(cleaned)
            
            return {
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
                'namespace': self._get_namespace(cleaned),
                'classes': self.parse_classes(cleaned),
                'functions': self.parse_functions(cleaned),
                'dependencies': self._collect_dependencies(cleaned)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

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
        for line in lines:
            current_depth += line.count('{') - line.count('}')
            max_depth = max(max_depth, current_depth)
        metrics.max_depth = max_depth
        
        return metrics

    def parse_functions(self, content: str) -> List[Dict[str, Any]]:
        """Parse method declarations."""
        methods = []
        method_pattern = (
            r'(?:public|private|protected|internal|static|virtual|override|abstract|async|\s)+'
            r'(?:<[^>]+>)?'
            r'\s+(?:[a-zA-Z0-9_<>[\],\s]+)'
            r'\s+([a-zA-Z0-9_]+)\s*\((.*?)\)'
        )
        
        for match in re.finditer(method_pattern, content):
            name = match.group(1)
            if name not in ('if', 'for', 'while', 'switch'):
                params = self._parse_parameters(match.group(2))
                decorators = self._get_attributes(content, match.start())
                methods.append({
                    'name': name,
                    'parameters': params,
                    'decorators': decorators,
                    'is_async': bool(re.search(r'\basync\b', content[match.start():match.end()]))
                })
        
        return methods

    def parse_classes(self, content: str) -> List[Dict[str, Any]]:
        """Parse class declarations."""
        classes = []
        class_pattern = (
            r'(?:public|private|protected|internal|static|sealed|abstract|\s)+'
            r'class\s+([a-zA-Z0-9_]+)(?:<[^>]+>)?'
            r'(?:\s*:\s*([^{]+))?'
        )
        
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            inheritance = match.group(2)
            bases = []
            if inheritance:
                bases = [base.strip() for base in inheritance.split(',')]
            
            start_pos = content.find('{', match.end())
            if start_pos != -1:
                class_body = self._extract_block_content(content[start_pos:])
                methods = self.parse_functions(class_body)
                properties = self._get_properties(class_body)
                
                classes.append({
                    'name': class_name,
                    'methods': methods,
                    'properties': properties,
                    'bases': bases,
                    'attributes': self._get_attributes(content, match.start())
                })
        
        return classes

    def parse_imports(self, content: str) -> List[str]:
        """Parse using statements."""
        imports = set()
        import_pattern = r'using\s+([^;]+);'
        
        for match in re.finditer(import_pattern, content):
            import_stmt = match.group(1).strip()
            if not import_stmt.startswith('('):  # Exclude using statements in using blocks
                imports.add(import_stmt)
                
        return sorted(list(imports))

    def _get_namespace(self, content: str) -> str:
        """Extract namespace information."""
        namespace_pattern = r'namespace\s+([^\s{;]+)'
        match = re.search(namespace_pattern, content)
        return match.group(1) if match else ''

    def _parse_parameters(self, params_str: str) -> List[Dict[str, str]]:
        """Parse method parameters."""
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
                    params.append(self._process_parameter(param))
                current_param = []
                continue
            current_param.append(char)
            
        if current_param:
            param = ''.join(current_param).strip()
            if param:
                params.append(self._process_parameter(param))
                
        return params

    def _process_parameter(self, param: str) -> Dict[str, str]:
        """Process a single parameter string."""
        parts = param.split('=', 1)
        param = parts[0].strip()
        param_parts = param.split()
        
        if len(param_parts) == 1:
            return {'name': param_parts[0]}
        else:
            return {
                'name': param_parts[-1],
                'type': ' '.join(param_parts[:-1])
            }

    def _get_attributes(self, content: str, position: int) -> List[str]:
        """Extract C# attributes (decorators)."""
        attributes = []
        code_before = content[:position]
        last_newline = code_before.rfind('\n')
        relevant_code = code_before[last_newline + 1:]
        
        attribute_pattern = r'\[([^\]]+)\]'
        matches = re.finditer(attribute_pattern, relevant_code)
        
        for match in matches:
            attr = match.group(1)
            if '(' in attr:
                attr = attr[:attr.find('(')]
            attributes.append(attr.strip())
            
        return attributes

    def _get_properties(self, class_body: str) -> List[Dict[str, Any]]:
        """Extract C# properties."""
        properties = []
        prop_pattern = (
            r'(?:public|private|protected|internal|static|virtual|override|abstract|\s)+'
            r'(?:[a-zA-Z0-9_<>[\],\s]+)'
            r'\s+([a-zA-Z0-9_]+)\s*{\s*(?:get|set|init)[^}]*}'
        )
        
        for match in re.finditer(prop_pattern, class_body):
            properties.append({
                'name': match.group(1),
                'attributes': self._get_attributes(class_body, match.start())
            })
            
        return properties

    def _collect_dependencies(self, content: str) -> Dict[str, List[str]]:
        """Extract .NET dependencies and framework information."""
        dependencies = {
            'frameworks': [],
            'packages': []
        }
        
        # Extract target framework
        framework_pattern = r'<TargetFramework[s]?>([^<]+)</TargetFramework[s]?>'
        framework_matches = re.finditer(framework_pattern, content)
        for match in framework_matches:
            frameworks = match.group(1).split(';')
            dependencies['frameworks'].extend(frameworks)
            
        # Extract package references
        package_pattern = r'<PackageReference\s+Include="([^"]+)"\s+Version="([^"]+)"'
        package_matches = re.finditer(package_pattern, content)
        for match in package_matches:
            package = f"{match.group(1)}@{match.group(2)}"
            dependencies['packages'].append(package)
            
        return dependencies

    def _extract_block_content(self, content: str) -> str:
        """Extract content between matching braces."""
        nesting_level = 0
        block_content = []
        
        for i, char in enumerate(content):
            if char == '{':
                nesting_level += 1
            elif char == '}':
                nesting_level -= 1
                if nesting_level == 0:
                    return ''.join(block_content)
            if nesting_level > 0:
                block_content.append(char)
                
        return ''.join(block_content)

    def clean_content(self, content: str) -> str:
        """Clean C# content by removing comments and unnecessary whitespace."""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        content = re.sub(r'/\*[\s\S]*?\*/', '', content)
        
        # Clean and normalize whitespace
        lines = [line.strip() for line in content.splitlines()]
        return '\n'.join(line for line in lines if line)