import re
from typing import Dict, Any, List
from src.handlers.base import BaseHandler, BaseParserMixin, CodeMetrics
from src.core.config import LanguageConfig

class PythonHandler(BaseHandler, BaseParserMixin):
    """Handler for Python source code analysis."""
    config = LanguageConfig(
        name="python",
        file_extensions={'.py'},
        single_line_comment='#',
        test_file_patterns={
            r'test_.*\.py$',
            r'.*_test\.py$',
            r'.*_tests\.py$'
        },
        keywords={
            'def', 'class', 'if', 'elif', 'else', 'for', 'while',
            'try', 'except', 'with', 'async', 'await'
        },
        complexity_patterns={
            r'\bif\b', r'\belif\b', r'\bfor\b', r'\bwhile\b',
            r'\bexcept\b', r'\bwith\b', r'\basync\s+def\b'
        }
    )

    def analyze_code(self, content: str) -> Dict[str, Any]:
        """Analyze Python code content."""
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
                    'max_depth': metrics.max_depth
                },
                'imports': self.parse_imports(cleaned),
                'functions': self.parse_functions(cleaned),
                'classes': self.parse_classes(cleaned)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def clean_content(self, content: str) -> str:
        """Clean Python content by removing comments and empty lines."""
        if not content:
            return ""
        lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                lines.append(line)
        return '\n'.join(lines)

    def _calculate_metrics(self, content: str) -> CodeMetrics:
        """Calculate code metrics."""
        metrics = CodeMetrics()
        lines = content.splitlines()
        metrics.lines_of_code = len(lines)
        metrics.blank_lines = sum(1 for line in lines if not line.strip())
        complexity = 1
        for pattern in self.config.complexity_patterns:
            complexity += len(re.findall(pattern, content))
        metrics.complexity = complexity
        current_depth = 0
        max_depth = 0
        for line in lines:
            indent = len(line) - len(line.lstrip())
            depth = indent // 4  # Assuming 4-space indentation
            current_depth = depth
            max_depth = max(max_depth, current_depth)
        metrics.max_depth = max_depth
        return metrics

    def parse_functions(self, content: str) -> List[Dict[str, Any]]:
        """Parse function declarations."""
        functions = []
        pattern = r'(?:async\s+)?def\s+([a-zA-Z_]\w*)\s*\([^)]*\)'
        for match in re.finditer(pattern, content):
            is_async = 'async' in content[match.start():match.end()]
            functions.append({
                'name': match.group(1),
                'is_async': is_async
            })
        return functions

    def parse_classes(self, content: str) -> List[Dict[str, Any]]:
        """Parse class declarations."""
        classes = []
        class_pattern = r'class\s+([a-zA-Z_]\w*)\s*(?:\([^)]*\))?:'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            start_pos = match.end()
            classes.append({
                'name': class_name,
                'methods': self.parse_functions(content[start_pos:])
            })
        return classes

    def parse_imports(self, content: str) -> List[str]:
        """Parse import statements."""
        imports = set()
        import_pattern = r'(?:from\s+(\S+)\s+)?import\s+([^;\n]+)'
        for match in re.finditer(import_pattern, content):
            module = match.group(1)
            names = match.group(2).strip()
            if module:
                imports.add(module)
            for name in names.split(','):
                name = name.strip().split()[0]  # Handle 'as' aliases
                imports.add(name)
        return sorted(list(imports))