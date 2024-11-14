# Mr Plow Through Code 🚜 

A robust code context generator that plows through your repositories to create comprehensive, LLM-ready code contexts.

> "Call Mr. Plow, that's my name. That name again is Mr. Plow!" - But for code analysis

## Overview

Mr Plow Through Code is a powerful Python tool designed to analyze code repositories and generate detailed context files optimized for Large Language Models (LLMs). It systematically processes your codebase, extracting relevant information, metrics, and relationships to help LLMs better understand and work with your code.

## Features

- **Multi-Language Support**
  - Python
  - JavaScript/TypeScript (including React)
  - C#/.NET
  - Easily extensible for other languages

- **Comprehensive Analysis**
  - Code structure and metrics
  - Function and class declarations
  - Dependencies and imports
  - React components and hooks
  - Code complexity metrics
  - Maintainability index
  - Documentation strings
  - Class relationships

- **Smart Processing**
  - Asynchronous file processing
  - Automatic encoding detection
  - Configurable file size limits
  - Test file filtering
  - Exclusion patterns
  - Progress tracking
  - Detailed statistics

- **Output Formats**
  - JSONL (default)
  - JSON
  - Structured format optimized for LLM consumption

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mr-plow-through-code.git
cd mr-plow-through-code

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python -m src.cli /path/to/your/repo
```

### Advanced Options

```bash
python -m src.cli /path/to/your/repo \
    --output analysis.jsonl \
    --format jsonl \
    --include-tests \
    --max-size 2097152 \
    --verbose
```

### Arguments

- `path`: Path to code directory (required)
- `-o, --output`: Output file path
- `-f, --format`: Output format (jsonl or json)
- `--include-tests`: Include test files in analysis
- `--max-size`: Maximum file size in bytes (default: 1MB)
- `-v, --verbose`: Enable verbose output

## Output Structure

The tool generates a JSONL file with the following structure:

```json
// Metadata record (first line)
{
  "timestamp": "2024-11-14T02:14:06.414263",
  "repository_root": "/path/to/repo",
  "total_files": 13,
  "statistics": {
    "processed_files": 13,
    "skipped_files": 2,
    "failed_files": 0,
    "total_raw_size": 66000,
    "total_cleaned_size": 61174,
    "processing_time": 0.054,
    "file_types": {"py": 13},
    "failed_files_info": []
  }
}

// File records (subsequent lines)
{
  "path": "src/core/processor.py",
  "type": "py",
  "analysis": {
    "metrics": {
      "lines_of_code": 242,
      "complexity": 50,
      "max_depth": 7
    },
    "imports": [...],
    "functions": [...],
    "classes": [...]
  },
  "size": 11000,
  "content": "..."
}
```

## Language Support Details

### Python
- Full parsing of functions, classes, and modules
- Import analysis
- Docstring extraction
- Complexity metrics
- Type hints analysis

### JavaScript/TypeScript
- React component detection
- Hook usage analysis
- ES6+ syntax support
- JSX/TSX parsing
- Module imports/exports
- Class and function analysis

### C#/.NET
- Namespace analysis
- Class inheritance
- Method attributes
- Property detection
- Using statements
- .NET-specific patterns

## Configuration

Default configurations can be modified in `src/core/config.py`:

```python
@dataclass
class ProcessorConfig:
    target_dir: Path
    output_file: Optional[str] = None
    include_tests: bool = False
    output_format: str = 'jsonl'
    max_file_size: int = 1024 * 1024  # 1MB
    worker_count: int = 4
    excluded_patterns: Set[str] = field(default_factory=lambda: {
        '.git', '__pycache__', 'node_modules', 'venv',
        'build', 'dist', '.pytest_cache', '.mypy_cache'
    })
```

## Extending Language Support

To add support for a new language:

1. Create a new handler in `src/handlers/plugins/`
2. Extend `BaseHandler` and implement required methods
3. Define language configuration
4. Handler will be automatically loaded

Example:
```python
class NewLanguageHandler(BaseHandler, BaseParserMixin):
    config = LanguageConfig(
        name="newlang",
        file_extensions={'.nl', '.newlang'},
        single_line_comment='//',
        # ... additional configuration
    )
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details.

## Future Plans

- [ ] Add support for more languages (Go, Ruby, Java)
- [ ] Enhanced semantic analysis
- [ ] Integration with popular IDEs
- [ ] Parallelized processing for large codebases
- [ ] Custom plugin system for analysis rules
- [ ] API for direct LLM integration

## Acknowledgments

Named after the iconic Simpsons character, Mr. Plow, this tool aims to clear the path for better code understanding and analysis, just as Mr. Plow cleared the snowy streets of Springfield.
