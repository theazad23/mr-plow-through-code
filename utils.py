import hashlib
from pathlib import Path
import chardet
from typing import Optional
from logging_config import setup_logger

logger = setup_logger(__name__)

def get_file_encoding(file_path: Path) -> str:
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        logger.debug(f"Detected encoding {result['encoding']} for file {file_path}")
        return result['encoding'] or 'utf-8'

def read_file_safely(file_path: Path) -> Optional[str]:
    try:
        encoding = get_file_encoding(file_path)
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        for enc in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    logger.debug(f"Successfully read {file_path} with encoding {enc}")
                    return f.read()
            except UnicodeDecodeError:
                continue
    logger.error(f"Failed to read {file_path} with any encoding")
    return None

def calculate_file_hash(file_path: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for byte_block in iter(lambda: f.read(4096), b''):
            sha256_hash.update(byte_block)
    logger.debug(f"Calculated SHA-256 hash for {file_path}")
    return sha256_hash.hexdigest()
