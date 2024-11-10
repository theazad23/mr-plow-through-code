from typing import Dict, Any
from .base_handler import BaseCodeHandler, CodeMetrics
from ..constants import AnalysisKeys as Keys
import logging
import re

class TextHandler(BaseCodeHandler):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        # Text files don't have comments
        self.single_line_comment = None
        self.multi_line_comment_start = None
        self.multi_line_comment_end = None

    def analyze_code(self, content: str) -> Dict[str, Any]:
        """Analyzes text content and provides metrics."""
        try:
            if content is None:
                content = ""  # Convert None to empty string
                
            cleaned = self.clean_content(content)
            metrics = self.count_lines(cleaned)  # Using the fixed base handler count_lines
            
            # Split content into words, sentences, and paragraphs safely
            words = re.findall(r'\b\w+\b', cleaned) or []
            sentences = [s.strip() for s in re.split(r'[.!?]+', cleaned) if s.strip()] or []
            paragraphs = [p.strip() for p in cleaned.split('\n\n') if p.strip()] or []

            # Calculate averages safely
            avg_word_length = (sum(len(word) for word in words) / len(words)) if words else 0
            avg_sentence_length = (len(words) / len(sentences)) if sentences else 0
            
            metrics.complexity = self._calculate_text_complexity(cleaned)
            metrics.max_depth = self._calculate_indentation_depth(cleaned)

            return {
                Keys.SUCCESS: True,
                Keys.METRICS: {
                    **Keys.metrics_result(metrics),
                    'word_count': len(words),
                    'sentence_count': len(sentences),
                    'paragraph_count': len(paragraphs),
                    'avg_word_length': round(avg_word_length, 2),
                    'avg_sentence_length': round(avg_sentence_length, 2)
                }
            }
        except Exception as e:
            self.logger.error(f"Error analyzing text content: {str(e)}")
            return {Keys.SUCCESS: False, Keys.ERROR: str(e)}

    def _calculate_text_complexity(self, content: str) -> int:
        """Calculates text complexity based on various factors."""
        if not content:
            return 1
            
        try:
            special_chars = len(re.findall(r'[^a-zA-Z0-9\s]', content))
            numbers = len(re.findall(r'\d+', content))
            punctuation = len(re.findall(r'[.,!?;:]', content))
            complex_words = len([w for w in re.findall(r'\b\w+\b', content) if len(w) > 6])
            
            complexity = (special_chars + numbers + punctuation + complex_words) // 10
            return max(1, complexity)
        except Exception as e:
            self.logger.error(f"Error calculating text complexity: {str(e)}")
            return 1

    def _calculate_indentation_depth(self, content: str) -> int:
        """Calculates the maximum indentation depth of the text."""
        if not content:
            return 0
            
        try:
            max_depth = 0
            for line in content.splitlines():
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    depth = indent // 2
                    max_depth = max(max_depth, depth)
            return max_depth
        except Exception as e:
            self.logger.error(f"Error calculating indentation depth: {str(e)}")
            return 0

    def clean_content(self, content: str) -> str:
        """Cleans the text content while preserving important formatting."""
        try:
            if content is None:
                return ""
                
            # Remove null bytes and normalize line endings
            content = content.replace('\x00', '')
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Clean lines while preserving non-empty content
            lines = []
            for line in content.splitlines():
                cleaned_line = line.rstrip()
                if cleaned_line:  # Keep non-empty lines
                    lines.append(cleaned_line)
                    
            return '\n'.join(lines)
        except Exception as e:
            self.logger.error(f"Error cleaning text content: {str(e)}")
            return ""