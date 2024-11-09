from datetime import datetime
import json
import asyncio
import aiofiles
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from rich.progress import Progress

from .handler_registry import CodeHandlerRegistry
from config import ProcessorConfig
from utils import calculate_file_hash, read_file_safely

class ContentProcessor:
    """Processes source code files using language-specific handlers."""

    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.registry = CodeHandlerRegistry()
        self.logger = logging.getLogger(__name__)
        if config.verbose:
            self.logger.setLevel(logging.DEBUG)
        
        # Get repository name from the target directory
        self.repo_name = self.config.target_dir.name
        
        # Set output directory to /output in the project root
        self.output_dir = Path(__file__).parent.parent / 'output'
        self.output_dir.mkdir(exist_ok=True)
        
        # Set default output file name using repo name
        if not self.config.output_file:
            self.config.output_file = str(self.output_dir / f'{self.repo_name}_code_context.{self.config.output_format}')
        
        if self.config.included_extensions is None:
            self.config.included_extensions = self.registry.get_supported_extensions()
        
        self.stats = {
            'processed_files': 0,
            'skipped_files': 0,
            'failed_files': 0,
            'total_raw_size': 0,
            'total_cleaned_size': 0,
            'processing_time': 0,
            'total_files': 0,
            'file_types': {},
            'failed_files_info': []
        }
    
    async def should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed."""
        try:
            if not file_path.is_file():
                self.logger.debug(f'Skipping {file_path}: not a file')
                return False
                
            size = file_path.stat().st_size
            if size > self.config.max_file_size:
                self.logger.debug(
                    f'Skipping {file_path}: size {size} exceeds limit '
                    f'{self.config.max_file_size}'
                )
                return False
                
            if not self.registry.supports_extension(file_path.suffix):
                self.logger.debug(
                    f'Skipping {file_path}: extension {file_path.suffix} not supported'
                )
                return False
                
            rel_path = str(file_path.relative_to(self.config.target_dir))
            if any(pattern in rel_path for pattern in self.config.excluded_patterns):
                self.logger.debug(f'Skipping {file_path}: matches excluded pattern')
                return False
                
            self.logger.debug(f'Will process {file_path}')
            return True
            
        except Exception as e:
            self.logger.warning(f'Error checking file {file_path}: {e}')
            return False

    async def process_file(self, file_path: Path) -> Optional[Dict]:
        """Process a single file using appropriate language handler."""
        try:
            if not await self.should_process_file(file_path):
                self.stats['skipped_files'] += 1
                return None

            self.logger.debug(f'Starting to process {file_path}')
            
            # Get the appropriate handler
            handler = self.registry.get_handler_for_file(file_path)
            if not handler:
                self.logger.warning(f'No handler found for {file_path}')
                self.stats['skipped_files'] += 1
                return None

            # Read and process the file
            raw_size = file_path.stat().st_size
            self.stats['total_raw_size'] += raw_size
            
            content = read_file_safely(file_path, self.logger)
            if not content or not content.strip():
                self.logger.debug(f'Skipping empty file: {file_path}')
                self.stats['skipped_files'] += 1
                return None

            # Clean and analyze the content
            try:
                cleaned_content = handler.clean_content(content)
                if not cleaned_content.strip():
                    self.logger.debug(f'Skipping {file_path}: empty after cleaning')
                    self.stats['skipped_files'] += 1
                    return None
                    
                analysis = handler.analyze_code(cleaned_content)
                if not analysis.get('success', False):
                    error_msg = analysis.get('error', 'Unknown analysis error')
                    self.logger.error(f'Analysis failed for {file_path}: {error_msg}')
                    self.stats['failed_files'] += 1
                    self.stats['failed_files_info'].append({
                        'file': str(file_path),
                        'error': f'Analysis error: {error_msg}'
                    })
                    return None

            except Exception as e:
                self.logger.error(f'Failed to process {file_path}: {e}')
                self.stats['failed_files'] += 1
                self.stats['failed_files_info'].append({
                    'file': str(file_path),
                    'error': str(e)
                })
                return None

            # Update statistics
            file_type = file_path.suffix.lstrip('.')
            cleaned_size = len(cleaned_content.encode('utf-8'))
            self.stats['total_cleaned_size'] += cleaned_size
            self.stats['file_types'][file_type] = (
                self.stats['file_types'].get(file_type, 0) + 1
            )
            self.stats['processed_files'] += 1

            return {
                'path': str(file_path.relative_to(self.config.target_dir)),
                'type': file_type,
                'analysis': analysis,
                'size': cleaned_size,
                'content': cleaned_content,
                'hash': calculate_file_hash(file_path)
            }

        except Exception as e:
            self.logger.error(f'Unexpected error processing {file_path}: {e}')
            self.stats['failed_files'] += 1
            self.stats['failed_files_info'].append({
                'file': str(file_path),
                'error': f'Unexpected error: {str(e)}'
            })
            return None

    async def process(self) -> dict:
        """Process all files in the target directory."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.logger.info(f'Starting processing of {self.config.target_dir}')
            
            # Get all files that should be processed
            files = [
                f for f in self.config.target_dir.rglob('*') 
                if await self.should_process_file(f)
            ]
            self.stats['total_files'] = len(files)

            results = []
            with Progress() as progress:
                task = progress.add_task('[cyan]Processing files...', total=len(files))
                
                for file_path in files:
                    result = await self.process_file(file_path)
                    if result:
                        results.append(result)
                    progress.update(task, advance=1)

            # Calculate processing time
            end_time = asyncio.get_event_loop().time()
            self.stats['processing_time'] = end_time - start_time

            # Save results
            await self.save_results(results)

            # Log any failures
            if self.stats['failed_files'] > 0:
                self.logger.error('\nFailed files details:')
                for fail_info in self.stats['failed_files_info']:
                    self.logger.error(f"\nFile: {fail_info['file']}")
                    self.logger.error(f"Error: {fail_info['error']}")

            return self.stats

        except Exception as e:
            self.logger.error(f'Error during processing: {e}')
            raise
        
    async def save_results(self, results: List[Dict]) -> None:
        """Save processing results to file."""
        try:
            # Ensure output file path is absolute
            output_path = Path(self.config.output_file)
            if not output_path.is_absolute():
                output_path = self.output_dir / output_path

            self.logger.info(f'Saving results to {output_path}')
            
            # Create metadata
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'repository_root': str(self.config.target_dir),
                'total_files': len(results),
                'statistics': self.stats
            }

            # Ensure the directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save in appropriate format
            if self.config.output_format == 'jsonl':
                with open(output_path, 'w', encoding='utf-8') as f:
                    # Write metadata first
                    f.write(json.dumps(metadata) + '\n')
                    # Write each result on a new line
                    for result in results:
                        f.write(json.dumps(result) + '\n')
            else:  # json format
                output = {
                    'metadata': metadata,
                    'files': results
                }
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(output, f, indent=2)

            self.logger.info(f'Results saved successfully to {output_path}')
            
        except Exception as e:
            self.logger.error(f'Error saving results: {e}')
            raise