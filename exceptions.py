from logging_config import setup_logger

logger = setup_logger(__name__)

class CodeContextError(Exception):
    """Base exception for code context related errors."""
    def __init__(self, message: str):
        logger.error(f"CodeContextError: {message}")
        super().__init__(message)

class FileProcessingError(CodeContextError):
    """Raised when there's an error processing a file."""
    def __init__(self, message: str):
        logger.error(f"FileProcessingError: {message}")
        super().__init__(message)

class ConfigurationError(CodeContextError):
    """Raised when there's an invalid configuration."""
    def __init__(self, message: str):
        logger.error(f"ConfigurationError: {message}")
        super().__init__(message)