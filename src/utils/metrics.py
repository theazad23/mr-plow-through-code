from dataclasses import dataclass
from typing import Dict, List, Set, Optional
import re

@dataclass
class ComplexityMetrics:
    """Detailed code complexity metrics."""
    cyclomatic_complexity: int = 1
    cognitive_complexity: int = 0
    halstead_metrics: Dict[str, float] = None
    maintainability_index: float = 100.0

class MetricsCalculator:
    """Utility class for calculating various code metrics."""
    
    @staticmethod
    def calculate_complexity(content: str, patterns: Set[str]) -> int:
        """Calculate cyclomatic complexity based on patterns."""
        try:
            complexity = 1  # Base complexity
            for pattern in patterns:
                complexity += len(re.findall(pattern, content))
            return complexity
        except Exception:
            return 1

    @staticmethod
    def calculate_cognitive_complexity(content: str) -> int:
        """
        Calculate cognitive complexity based on:
        - Nesting depth
        - Number of control structures
        - Logical operators
        """
        complexity = 0
        current_depth = 0
        lines = content.splitlines()
        
        for line in lines:
            # Increment for nesting
            indent = len(line) - len(line.lstrip())
            new_depth = indent // 4
            if new_depth > current_depth:
                complexity += new_depth
            current_depth = new_depth
            
            # Increment for control structures
            if re.search(r'\b(if|while|for|catch)\b', line):
                complexity += 1
            
            # Increment for logical operators
            complexity += len(re.findall(r'&&|\|\|', line))
            
        return complexity

    @staticmethod
    def calculate_halstead_metrics(content: str) -> Dict[str, float]:
        """
        Calculate Halstead complexity metrics:
        - Program length (N)
        - Vocabulary size (n)
        - Program volume (V)
        - Difficulty (D)
        """
        try:
            # Count operators and operands
            operators = set()
            operands = set()
            total_operators = 0
            total_operands = 0
            
            # Basic operators pattern
            operator_pattern = r'[+\-*/=<>!&|^~]|->|<<|>>|\+\+|--|==|!=|<=|>=|&&|\|\||::|<<='
            
            for match in re.finditer(operator_pattern, content):
                operators.add(match.group())
                total_operators += 1
            
            # Identify operands (variables, literals, etc.)
            operand_pattern = r'\b[a-zA-Z_]\w*\b|\b\d+\b|"[^"]*"|\'[^\']*\''
            for match in re.finditer(operand_pattern, content):
                operands.add(match.group())
                total_operands += 1
            
            # Calculate metrics
            n1 = len(operators)  # Unique operators
            n2 = len(operands)   # Unique operands
            N1 = total_operators # Total operators
            N2 = total_operands  # Total operands
            
            vocabulary = n1 + n2
            length = N1 + N2
            volume = length * (vocabulary.bit_length() if vocabulary > 0 else 1)
            difficulty = (n1 * N2) / (2 * n2) if n2 > 0 else 0
            
            return {
                'vocabulary': vocabulary,
                'length': length,
                'volume': volume,
                'difficulty': difficulty,
                'effort': volume * difficulty
            }
        except Exception:
            return {
                'vocabulary': 0,
                'length': 0,
                'volume': 0,
                'difficulty': 0,
                'effort': 0
            }

    @staticmethod
    def calculate_maintainability_index(content: str, halstead_volume: float) -> float:
        """
        Calculate maintainability index using:
        - Lines of code
        - Cyclomatic complexity
        - Halstead volume
        """
        try:
            loc = len(content.splitlines())
            cyclomatic = MetricsCalculator.calculate_complexity(
                content, 
                {r'\bif\b', r'\bwhile\b', r'\bfor\b', r'\bcatch\b'}
            )
            
            # Standard maintainability index formula
            mi = 171 - 5.2 * (halstead_volume ** 0.23) - 0.23 * cyclomatic - 16.2 * (loc ** 0.43)
            
            # Normalize to 0-100 scale
            return max(0, min(100, mi * 100 / 171))
        except Exception:
            return 100.0  # Default to perfect maintainability on error