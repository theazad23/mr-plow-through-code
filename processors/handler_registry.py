from typing import Dict, Type, Optional
from pathlib import Path
from logging_config import setup_logger
from processors.handlers.react_handler import ReactHandler
from processors.handlers.base_handler import BaseCodeHandler
from processors.handlers.python_handler import PythonHandler
from processors.handlers.javascript_handler import JavaScriptHandler
from processors.handlers.java_handler import JavaHandler
from processors.handlers.csharp_handler import CSharpHandler
from processors.handlers.text_handler import TextHandler

logger = setup_logger(__name__)

class CodeHandlerRegistry:
    """Registry for language-specific code handlers."""
    
    def __init__(self):
        self._handlers: Dict[str, Type[BaseCodeHandler]] = {}
        self._extension_mapping: Dict[str, str] = {}
        self._initialize_handlers()
        
    def _initialize_handlers(self):
        """Initialize built-in handlers and their file extensions."""
        self.register_handler('python', PythonHandler, ['.py'])
        self.register_handler('javascript', JavaScriptHandler, ['.js'])
        self.register_handler('react', ReactHandler, ['.jsx', '.tsx'])
        self.register_handler('typescript', JavaScriptHandler, ['.ts'])
        self.register_handler('text', TextHandler, ['.txt', '.md', '.rst', '.log'])
        self.register_handler('java', JavaHandler, ['.java'])
        self.register_handler('csharp', CSharpHandler, [
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
        ])
        # self.register_handler('cpp', CppHandler, ['.cpp', '.cc', '.cxx', '.h', '.hpp'])
        # self.register_handler('ruby', RubyHandler, ['.rb', '.rake'])
        # self.register_handler('go', GoHandler, ['.go'])
        # self.register_handler('rust', RustHandler, ['.rs'])
        
    def register_handler(self, language: str, handler_class: Type[BaseCodeHandler], 
                        extensions: list[str]) -> None:
        """
        Register a new language handler.
        
        Args:
            language: Language identifier
            handler_class: Handler class implementing BaseCodeHandler
            extensions: List of file extensions handled by this handler
        """
        if not issubclass(handler_class, BaseCodeHandler):
            raise ValueError(f"Handler class must inherit from BaseCodeHandler: {handler_class}")
            
        self._handlers[language] = handler_class
        for ext in extensions:
            if ext in self._extension_mapping:
                logger.warning(
                    f"Extension {ext} is already registered to {self._extension_mapping[ext]}. "
                    f"Overwriting with {language}"
                )
            self._extension_mapping[ext.lower()] = language
            
    def get_handler_for_file(self, file_path: Path) -> Optional[BaseCodeHandler]:
        """
        Get appropriate handler instance for a given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Handler instance or None if no handler is found
        """
        extension = file_path.suffix.lower()
        language = self._extension_mapping.get(extension)
        
        if not language:
            return None
            
        handler_class = self._handlers.get(language)
        if not handler_class:
            return None
            
        return handler_class()
        
    def supports_extension(self, extension: str) -> bool:
        """Check if an extension is supported."""
        return extension.lower() in self._extension_mapping
        
    def get_supported_extensions(self) -> set[str]:
        """Get all supported file extensions."""
        return set(self._extension_mapping.keys())
        
    def get_supported_languages(self) -> set[str]:
        """Get all supported programming languages."""
        return set(self._handlers.keys())