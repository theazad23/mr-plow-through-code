import ast
from typing import Dict, Any, List, Set
from .base_handler import BaseCodeHandler, CodeMetrics
from ..constants import AnalysisKeys as Keys
import logging

class PythonHandler(BaseCodeHandler):
    """Handler for Python source code analysis."""

    def __init__(self):
        super().__init__()
        self.single_line_comment = '#'
        self.logger = logging.getLogger(__name__)

    def analyze_code(self, content: str) -> Dict[str, Any]:
        """Analyze Python code content."""
        try:
            cleaned_content = self.clean_content(content)
            
            # Basic metrics
            metrics = self.count_lines(content)
            metrics.complexity = self._calculate_complexity(cleaned_content)
            metrics.max_depth = self._calculate_depth(cleaned_content)
            
            # Extract basic elements
            imports = []
            functions = []
            classes = []
            
            lines = cleaned_content.splitlines()
            current_class = None
            current_methods = []
            
            for line in lines:
                stripped = line.strip()
                
                # Skip empty lines and comments
                if not stripped or stripped.startswith('#'):
                    continue
                
                # Import detection
                if stripped.startswith('import '):
                    name = stripped[7:].split()[0].split('.')[0]
                    imports.append(name)
                elif stripped.startswith('from '):
                    parts = stripped.split()
                    if len(parts) >= 2:
                        name = parts[1].split('.')[0]
                        imports.append(name)
                
                # Function detection
                elif stripped.startswith('def '):
                    name = stripped[4:].split('(')[0]
                    is_async = 'async' in line[:line.find('def')]
                    if current_class:
                        current_methods.append({'name': name, 'is_async': is_async})
                    else:
                        functions.append({'name': name, 'is_async': is_async})
                
                # Class detection
                elif stripped.startswith('class '):
                    if current_class:
                        classes.append({
                            'name': current_class,
                            'methods': current_methods,
                            'bases': []
                        })
                    current_class = stripped[6:].split('(')[0].split(':')[0].strip()
                    current_methods = []
            
            # Add last class if any
            if current_class:
                classes.append({
                    'name': current_class,
                    'methods': current_methods,
                    'bases': []
                })
            
            return {
                Keys.SUCCESS: True,
                Keys.METRICS: Keys.metrics_result(metrics),
                Keys.IMPORTS: sorted(list(set(imports))),
                Keys.FUNCTIONS: functions,
                Keys.CLASSES: classes
            }
        except Exception as e:
            self.logger.error(f"Error analyzing Python code: {e}")
            return {Keys.SUCCESS: False, Keys.ERROR: str(e)}

    def _calculate_complexity(self, content: str) -> int:
        """Calculate complexity based on control structures."""
        complexity = 1
        keywords = ['if', 'elif', 'for', 'while', 'except', 'with', 'assert']
        lines = content.splitlines()
        
        for line in lines:
            stripped = line.strip()
            # Count control structures
            for keyword in keywords:
                if stripped.startswith(keyword + ' '):
                    complexity += 1
        
        return complexity

    def _calculate_depth(self, content: str) -> int:
        """Calculate code nesting depth."""
        max_depth = 0
        current_depth = 0
        lines = content.splitlines()
        
        for line in lines:
            stripped = line.rstrip()
            # Count leading spaces
            indent = len(line) - len(line.lstrip())
            depth = indent // 4  # Assuming 4-space indentation
            current_depth = depth
            max_depth = max(max_depth, current_depth)
        
        return max_depth

    def clean_content(self, content: str) -> str:
        """Clean Python content by removing comments and empty lines."""
        lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                lines.append(line)
        return '\n'.join(lines)