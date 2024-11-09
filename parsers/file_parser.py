from pathlib import Path
from fnmatch import fnmatch
import logging
from parsers.gitignore_parser import GitignoreParser

logger = logging.getLogger(__name__)

class FileParser:
    def __init__(self, include_tests: bool=False):
        self.include_tests = include_tests
        self.test_patterns = {
            '**/test_*.py', '**/tests/*.py', '**/tests/**/*.py', 
            '**/*_test.py', '**/test/*.py', '**/test/**/*.py',
            '**/*.spec.js', '**/*.test.js', '**/test/*.js', '**/tests/*.js',
            '**/__tests__/**',
            # .NET test patterns
            '**/*.Tests.cs', '**/*Tests.cs', '**/Tests/**/*.cs',
            '**/*.Test.cs', '**/Test/**/*.cs', '**/Specs/**/*.cs',
            '**/MSTest/**/*.cs', '**/NUnit/**/*.cs', '**/xUnit/**/*.cs',
            '**/*.Testing.cs', '**/Testing/**/*.cs',
            # .NET integration test patterns
            '**/*.IntegrationTests.cs', '**/IntegrationTests/**/*.cs',
            # .NET UI test patterns
            '**/*.UITests.cs', '**/UITests/**/*.cs',
            # Test project patterns
            '**/test.csproj', '**/*.Test.csproj', '**/*.Tests.csproj'
        }
        
        self.ignore_patterns = {
            'node_modules', '.git', 'venv', '__pycache__', 'dist', 'build',
            '.min.', 'vendor/', '.DS_Store', '.env', '.coverage',
            'bundle.', 'package-lock.json', 'README.md', '.pytest_cache',
            'htmlcov', '.coverage', 'test-results', '*.pyc', '*.pyo',
            # .NET specific patterns
            'bin/', 'obj/', 'packages/', '.vs/', '*.suo', '*.user',
            'TestResults/', 'packages.config', '*.dbmdl', '*.jfm',
            '_ReSharper.*/', '*.dotCover', 'artifacts/',
            '.vscode/', '.idea/', '*.cache', '*.tmp',
            'project.lock.json', '*.nuget.props', '*.nuget.targets',
            'nuget.config', 'global.json', '.editorconfig',
            # Build output
            '**/Debug/', '**/Release/', '**/x64/', '**/x86/',
            # Documentation
            '**/doc/', '**/docs/', '*.xml',
            # Deployment
            '**/deploy/', '**/deployment/', '*.pubxml', '*.pubxml.user',
            # Local settings
            'appsettings.*.json', '*.Development.json', '*.Local.json'
        }
        
        self.file_categories = {
            'source': {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.cs', '.vb', '.fs', '.go', '.rb'},
            'react': {'.jsx', '.tsx'},
            'dotnet': {
                '.cs',      # C# source files
                '.vb',      # Visual Basic
                '.fs',      # F#
                '.cshtml',  # Razor views
                '.razor',   # Blazor components
                '.xaml',    # XAML UI
                '.csproj',  # C# project files
                '.fsproj',  # F# project files
                '.vbproj',  # VB project files
                '.sln',     # Solution files
                '.props',   # MSBuild property files
                '.targets', # MSBuild target files
                '.resx',    # Resource files
                '.settings',# Settings files
                '.config', # Configuration files
                '.asax',   # Global application class
                '.ashx',   # Generic handlers
                '.asmx',   # Web services
                '.aspx',   # Web forms
                '.ascx',   # User controls
                '.master', # Master pages
                '.sitemap' # Site navigation
            },
            'config': {
                '.json', '.yaml', '.yml', '.toml', '.ini', '.xml',
                '.config', '.props', '.targets', '.pubxml',
                'appsettings.json', 'web.config', 'app.config'
            },
            'doc': {'.md', '.rst', '.txt', '.docx', '.pdf'},
            'style': {'.css', '.scss', '.sass', '.less'},
            'template': {'.html', '.cshtml', '.razor', '.xaml', '.jinja', '.jinja2', '.tmpl'},
            'shell': {'.sh', '.bash', '.zsh', '.fish', '.bat', '.cmd', '.ps1'}
        }

    def get_file_type(self, file_path: Path) -> str:
        """Get the category of the file based on its extension."""
        ext = file_path.suffix.lower()
        
        # Special handling for .NET project files
        if ext in {'.csproj', '.fsproj', '.vbproj', '.props', '.targets'}:
            return 'dotnet-project'
            
        # Special handling for .NET config files
        if ext == '.config' or file_path.name in {'appsettings.json', 'web.config', 'app.config'}:
            return 'dotnet-config'
            
        # Check other categories
        for category, extensions in self.file_categories.items():
            if ext in extensions:
                return category
                
        return 'unknown'

    def should_process_file(self, file_path: Path, gitignore_parser) -> bool:
        try:
            if not file_path.exists() or not file_path.is_file():
                return False

            rel_path = str(file_path)
            rel_path_str = rel_path.replace('\\', '/')

            # Check gitignore rules
            if gitignore_parser and gitignore_parser.is_ignored(rel_path_str):
                return False

            # Check ignore patterns
            if any(p in rel_path for p in self.ignore_patterns):
                return False

            # Handle test files
            is_test = self.is_test_file(rel_path_str)
            if is_test and not self.include_tests:
                return False

            # Get file extension
            ext = file_path.suffix.lower()

            # Special handling for .NET files
            if ext in self.file_categories['dotnet']:
                # Skip certain .NET files that shouldn't be processed
                if any(skip_pattern in file_path.name.lower() for skip_pattern in {
                    'assemblyinfo.cs',
                    'temporary',
                    'designer.cs',
                    '.designer.cs',
                    '.generated.cs',
                    'reference.cs',
                    'migration'
                }):
                    return False
                return True

            # Check if extension is in any category
            valid_extensions = {ext for exts in self.file_categories.values() for ext in exts}
            return ext in valid_extensions

        except Exception as e:
            self.logger.error(f'Error checking file {file_path}: {e}')
            return False
    
    def is_test_file(self, file_path: str) -> bool:
        normalized_path = str(file_path).replace('\\', '/')
        return any(fnmatch(normalized_path, pattern) for pattern in self.test_patterns)