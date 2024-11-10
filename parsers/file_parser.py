from pathlib import Path
from typing import Optional, Dict, Any
import re

from logging_config import setup_logger
from .file_patterns_config import FilePatterns, default_patterns
from utils import read_file_safely
from exceptions import FileProcessingError

class FileParser:
    """Parser for handling file operations and content processing."""

    def __init__(self, patterns: Optional[FilePatterns] = None):
        """
        Initialize the FileParser with optional custom patterns.
        
        Args:
            patterns: Optional FilePatterns instance for custom pattern matching
        """
        self.patterns = patterns or default_patterns
        self.logger = setup_logger(__name__)

    def process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Process a single file and return its metadata and content.
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            Optional[Dict[str, Any]]: File metadata and content if processed successfully
        """
        try:
            if not self.should_process_file(file_path):
                self.logger.debug(f"Skipping file: {file_path}")
                return None

            content = read_file_safely(file_path)
            if not content:
                self.logger.warning(f"Could not read content from {file_path}")
                return None

            category = self.patterns.get_category(file_path)
            is_test = self.patterns.is_test_file(file_path)

            return {
                'path': str(file_path),
                'category': category,
                'is_test': is_test,
                'size': file_path.stat().st_size,
                'content': content,
                'extension': file_path.suffix.lower(),
                'relative_path': str(file_path.relative_to(file_path.parent.parent))
            }

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
            raise FileProcessingError(f"Failed to process {file_path}: {str(e)}")

    def should_process_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be processed based on configured patterns.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if the file should be processed
        """
        try:
            if not file_path.is_file():
                return False

            if self.patterns.should_ignore(file_path):
                return False

            if not self.patterns.is_supported_extension(file_path.suffix.lower()):
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking file {file_path}: {str(e)}")
            return False