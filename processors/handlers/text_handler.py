from typing import Dict, Any
from .base_handler import BaseCodeHandler, CodeMetrics
from ..constants import AnalysisKeys as Keys
import logging
import re

class TextHandler(BaseCodeHandler):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        # Text files don't have traditional comments, but we'll support basic markers
        self.single_line_comment = '#'  # Optional: for structured text files
        self.multi_line_comment_start = None
        self.multi_line_comment_end = None

    def analyze_code(self, content: str) -> Dict[str, Any]:
        try:
            cleaned = self.clean_content(content)
            metrics = self.count_lines(content)
            
            # Basic text analysis
            words = re.findall(r'\b\w+\b', cleaned)
            sentences = re.split(r'[.!?]+', cleaned)
            paragraphs = [p for p in cleaned.split('\n\n') if p.strip()]
            
            # Calculate average lengths
            avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
            avg_sentence_length = len(words) / len(sentences) if sentences else 0
            
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
        """Calculate a basic complexity score based on text structure"""
        try:
            # Count special characters, numbers, and punctuation as complexity indicators
            special_chars = len(re.findall(r'[^a-zA-Z0-9\s]', content))
            numbers = len(re.findall(r'\d+', content))
            punctuation = len(re.findall(r'[.,!?;:]', content))
            
            # Count words with more than 6 characters as "complex" words
            complex_words = len([w for w in re.findall(r'\b\w+\b', content) if len(w) > 6])
            
            # Basic complexity score
            complexity = (special_chars + numbers + punctuation + complex_words) // 10
            return max(1, complexity)
        except Exception as e:
            self.logger.error(f"Error calculating text complexity: {str(e)}")
            return 1

    def _calculate_indentation_depth(self, content: str) -> int:
        """Calculate maximum indentation depth of the text"""
        try:
            max_depth = 0
            for line in content.splitlines():
                # Calculate indentation level based on leading spaces/tabs
                indent = len(line) - len(line.lstrip())
                depth = indent // 2  # Assuming 2 spaces per indentation level
                max_depth = max(max_depth, depth)
            return max_depth
        except Exception as e:
            self.logger.error(f"Error calculating indentation depth: {str(e)}")
            return 0

    def clean_content(self, content: str) -> str:
        """Clean the text content while preserving structure"""
        try:
            # Remove any null bytes or invalid characters
            content = content.replace('\x00', '')
            
            # Normalize line endings
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # Remove trailing whitespace while preserving indentation
            lines = [line.rstrip() for line in content.splitlines()]
            
            # Remove empty lines at the start and end while preserving internal empty lines
            while lines and not lines[0].strip():
                lines.pop(0)
            while lines and not lines[-1].strip():
                lines.pop()
                
            return '\n'.join(lines)
        except Exception as e:
            self.logger.error(f"Error cleaning text content: {str(e)}")
            return content