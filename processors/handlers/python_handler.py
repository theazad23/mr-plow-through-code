import ast
from typing import Dict, Any, List, Set
from .base_handler import BaseCodeHandler, CodeMetrics
from ..constants import AnalysisKeys as Keys

class PythonHandler(BaseCodeHandler):
    """Handler for Python source code analysis."""
    
    def __init__(self):
        super().__init__()
        self.single_line_comment = '#'
        self.multi_line_comment_start = '"""'
        self.multi_line_comment_end = '"""'
        
    def analyze_code(self, content: str) -> Dict[str, Any]:
        try:
            tree = ast.parse(content)
            metrics = self.count_lines(content)
            metrics.complexity = self._calculate_ast_complexity(tree)
            metrics.max_depth = self._calculate_ast_depth(tree)
            
            return {
                Keys.SUCCESS: True,
                Keys.METRICS: Keys.metrics_result(metrics),
                Keys.IMPORTS: list(self._collect_imports(tree)),
                Keys.FUNCTIONS: self._collect_functions(tree),
                Keys.CLASSES: self._collect_classes(tree)
            }
        except Exception as e:
            return {Keys.SUCCESS: False, Keys.ERROR: str(e)}
            
    def _calculate_ast_complexity(self, node: ast.AST) -> int:
        complexity = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor,
                                ast.ExceptHandler, ast.With, ast.AsyncWith,
                                ast.Assert, ast.Raise)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.IfExp):
                complexity += 1
        return max(1, complexity)
        
    def _calculate_ast_depth(self, node: ast.AST, current: int = 0) -> int:
        if isinstance(node, (ast.If, ast.For, ast.While, ast.With,
                           ast.AsyncFor, ast.AsyncWith)):
            current += 1
        max_depth = current
        for child in ast.iter_child_nodes(node):
            child_depth = self._calculate_ast_depth(child, current)
            max_depth = max(max_depth, child_depth)
        return max_depth
        
    def _collect_imports(self, tree: ast.AST) -> Set[str]:
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.add(name.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split('.')[0])
        return imports
        
    def _collect_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(Keys.function_info(
                    name=node.name,
                    args=[arg.arg for arg in node.args.args],
                    decorators=[ast.unparse(d) for d in node.decorator_list],
                    is_async=isinstance(node, ast.AsyncFunctionDef)
                ))
        return functions
        
    def _collect_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        methods.append(Keys.function_info(
                            name=child.name,
                            is_async=isinstance(child, ast.AsyncFunctionDef),
                            decorators=[ast.unparse(d) for d in child.decorator_list]
                        ))
                classes.append(Keys.class_info(
                    name=node.name,
                    methods=methods,
                    bases=[ast.unparse(base) for base in node.bases]
                ))
        return classes
        
    def clean_content(self, content: str) -> str:
        try:
            tree = ast.parse(content)
            return ast.unparse(tree)
        except:
            # Fallback to regex-based cleaning if AST parsing fails
            content = re.sub('#.*$', '', content, flags=re.MULTILINE)
            content = re.sub('"""[\s\S]*?"""', '', content)
            content = re.sub("'''[\s\S]*?'''", '', content)
            return '\n'.join(line for line in content.splitlines() if line.strip())