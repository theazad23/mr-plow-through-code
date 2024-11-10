import hashlib
from pathlib import Path
import chardet
from typing import Optional
from logging_config import setup_logger

logger = setup_logger(__name__)

def clean_python_docstrings(content: str) -> str:
    """Clean Python docstrings and comments without using AST."""
    lines = content.splitlines()
    cleaned_lines = []
    in_docstring = False
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            i += 1
            continue
            
        # Handle docstring starts
        if ('"""' in line or "'''" in line) and not in_docstring:
            quote_type = '"""' if '"""' in line else "'''"
            # Check if it's a single-line docstring
            if line.count(quote_type) == 2:
                i += 1
                continue
                
            in_docstring = True
            i += 1
            
            # Skip until we find the end of the docstring
            while i < len(lines):
                if quote_type in lines[i]:
                    in_docstring = False
                    i += 1
                    break
                i += 1
            continue
            
        # Skip comment lines
        if stripped.startswith('#'):
            i += 1
            continue
            
        # Include non-docstring, non-comment lines
        if not in_docstring:
            cleaned_lines.append(line)
        i += 1
    
    return '\n'.join(cleaned_lines)

def get_file_encoding(file_path: Path) -> str:
    """Detect file encoding."""
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        logger.debug(f"Detected encoding {result['encoding']} for file {file_path}")
        return result['encoding'] or 'utf-8'

def read_file_safely(file_path: Path) -> Optional[str]:
    """Read file with proper encoding and clean Python files."""
    try:
        encoding = get_file_encoding(file_path)
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
            if file_path.suffix.lower() == '.py':
                return clean_python_docstrings(content)
            return content
    except UnicodeDecodeError:
        for enc in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    content = f.read()
                    if file_path.suffix.lower() == '.py':
                        return clean_python_docstrings(content)
                    return content
            except UnicodeDecodeError:
                continue
        logger.error(f'Failed to read {file_path} with any encoding')
        return None

def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of file content."""
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b''):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()