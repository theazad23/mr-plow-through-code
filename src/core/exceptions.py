class CodeContextError(Exception):
    """Base exception for code context related errors."""
    pass

class HandlerNotFoundError(CodeContextError):
    """Raised when no handler is found for a file type."""
    pass

class FileProcessingError(CodeContextError):
    """Raised when there's an error processing a file."""
    pass

class ParsingError(CodeContextError):
    """Raised when there's an error parsing code content."""
    pass

class ConfigurationError(CodeContextError):
    """Raised when there's an invalid configuration."""
    pass

class PluginError(CodeContextError):
    """Raised when there's an error loading or using a plugin."""
    pass