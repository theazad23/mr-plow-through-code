from pathlib import Path
from typing import Dict, Type, Optional
import importlib
import pkgutil
import sys
from rich.console import Console
from src.handlers.base import BaseHandler
from src.core.exceptions import HandlerNotFoundError, PluginError

console = Console()

class HandlerRegistry:
    """Registry for language-specific code handlers with plugin support."""
    
    def __init__(self):
        self._handlers: Dict[str, Type[BaseHandler]] = {}
        self._extension_mapping: Dict[str, str] = {}
        console.print("[blue]Debug: Initializing HandlerRegistry[/blue]")
        self._load_plugins()
        console.print(f"[blue]Debug: Loaded handlers: {list(self._handlers.keys())}[/blue]")
        console.print(f"[blue]Debug: Loaded extensions: {list(self._extension_mapping.keys())}[/blue]")

    def _load_plugins(self) -> None:
        """Dynamically load handlers from the plugins directory."""
        try:
            # Get the plugins directory path
            plugins_dir = Path(__file__).parent.parent / 'handlers' / 'plugins'
            console.print(f"[blue]Debug: Loading plugins from: {plugins_dir}[/blue]")
            
            # Add the parent directory to Python path
            parent_dir = str(plugins_dir.parent.parent)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            # Import each plugin file
            for plugin_file in plugins_dir.glob('*.py'):
                if plugin_file.stem == '__init__':
                    continue
                    
                try:
                    console.print(f"[blue]Debug: Loading plugin: {plugin_file.stem}[/blue]")
                    spec = importlib.util.spec_from_file_location(
                        f"src.handlers.plugins.{plugin_file.stem}",
                        plugin_file
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module.__name__] = module
                        spec.loader.exec_module(module)
                        
                        # Find and register handler classes
                        for item_name in dir(module):
                            item = getattr(module, item_name)
                            if (isinstance(item, type) and 
                                issubclass(item, BaseHandler) and 
                                item != BaseHandler):
                                self.register_handler(item)
                                console.print(f"[green]Debug: Successfully registered handler: {item_name}[/green]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to load plugin {plugin_file.stem}: {str(e)}[/yellow]")
                    
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to load plugins: {str(e)}[/yellow]")

    def register_handler(self, handler_class: Type[BaseHandler]) -> None:
        """Register a handler class and its file extensions."""
        config = handler_class.config
        self._handlers[config.name] = handler_class
        for ext in config.file_extensions:
            if ext in self._extension_mapping:
                existing = self._extension_mapping[ext]
                console.print(
                    f"[yellow]Warning:[/yellow] Extension {ext} is already registered to {existing}. "
                    f"Overwriting with {config.name}"
                )
            self._extension_mapping[ext.lower()] = config.name
        console.print(f"[blue]Debug: Registered handler {config.name} for extensions {config.file_extensions}[/blue]")

    def get_handler(self, file_path: Path) -> Optional[BaseHandler]:
        """Get appropriate handler for a file type."""
        extension = file_path.suffix.lower()
        language = self._extension_mapping.get(extension)
        console.print(f"[blue]Debug: Looking for handler for extension {extension}, found language: {language}[/blue]")
        if not language:
            return None
        handler_class = self._handlers.get(language)
        if not handler_class:
            return None
        return handler_class()

    @property
    def supported_extensions(self) -> set[str]:
        """Get all supported file extensions."""
        return set(self._extension_mapping.keys())

    @property
    def supported_languages(self) -> set[str]:
        """Get all supported programming languages."""
        return set(self._handlers.keys())