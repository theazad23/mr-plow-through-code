import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import aiofiles
from rich.progress import Progress
from rich.console import Console
from rich.table import Table
from core.config import ProcessorConfig
from core.registry import HandlerRegistry
from core.exceptions import FileProcessingError, HandlerNotFoundError

console = Console()

class CodeContextProcessor:
    """Main processor for generating code context from source files."""
    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.registry = HandlerRegistry()
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

        # Find repository root (where the src directory is located)
        current_file = Path(__file__).resolve()
        self.repo_root = current_file.parent.parent.parent
        # Create output directory at repository root
        self.default_output_dir = self.repo_root / 'output'
        self.default_output_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[blue]Debug: Repository root: {self.repo_root}[/blue]")
        console.print(f"[blue]Debug: Output directory: {self.default_output_dir}[/blue]")

    async def process_directory(self) -> Dict[str, Any]:
        """Process all files in the target directory."""
        start_time = asyncio.get_event_loop().time()
        try:
            console.print("[bold blue]Starting code context generation...[/bold blue]")
            files = [
                f for f in self.config.target_dir.rglob('*')
                if await self._should_process_file(f)
            ]
            self.stats['total_files'] = len(files)
            results = []
            with Progress() as progress:
                task = progress.add_task(
                    "[cyan]Processing files...", 
                    total=len(files)
                )
                tasks = [
                    self.process_file(f) for f in files
                ]
                chunk_size = 100
                for i in range(0, len(tasks), chunk_size):
                    chunk = tasks[i:i + chunk_size]
                    chunk_results = await asyncio.gather(*chunk)
                    results.extend(
                        result for result in chunk_results if result is not None
                    )
                    progress.update(task, advance=len(chunk))

            self.stats['processing_time'] = (
                asyncio.get_event_loop().time() - start_time
            )
            await self._save_results(results)
            self._display_summary()
            return self.stats
        except Exception as e:
            console.print(f"[red]Error during processing: {str(e)}[/red]")
            raise


    async def process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Process a single file and return its analysis results."""
        try:
            # Get appropriate handler
            handler = self.registry.get_handler(file_path)
            if not handler:
                self.stats['skipped_files'] += 1
                return None
            
            # Read file content
            content = await self._read_file(file_path)
            if not content:
                self.stats['skipped_files'] += 1
                return None
            
            # Clean and analyze content
            cleaned_content = handler.clean_content(content)
            if not cleaned_content.strip():
                self.stats['skipped_files'] += 1
                return None
            
            # Analyze code
            analysis = handler.analyze_code(cleaned_content)
            if not analysis.get('success', False):
                self._record_failure(file_path, analysis.get('error', 'Unknown error'))
                return None
            
            # Update statistics
            file_type = file_path.suffix.lstrip('.')
            self.stats['file_types'][file_type] = (
                self.stats['file_types'].get(file_type, 0) + 1
            )
            self.stats['processed_files'] += 1
            
            # Calculate sizes
            raw_size = len(content.encode('utf-8'))
            cleaned_size = len(cleaned_content.encode('utf-8'))
            self.stats['total_raw_size'] += raw_size
            self.stats['total_cleaned_size'] += cleaned_size
            
            # Return results
            return {
                'path': str(file_path.relative_to(self.config.target_dir)),
                'type': file_type,
                'analysis': analysis,
                'size': cleaned_size,
                'content': cleaned_content
            }
            
        except HandlerNotFoundError:
            self.stats['skipped_files'] += 1
            return None
        except Exception as e:
            self._record_failure(file_path, str(e))
            return None

    async def _should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed."""
        try:
            if not file_path.is_file():
                return False
                
            # Check file extension
            if file_path.suffix.lower() not in self.registry.supported_extensions:
                return False
                
            # Check file size
            if file_path.stat().st_size > self.config.max_file_size:
                return False
                
            # Check excluded patterns
            rel_path = str(file_path.relative_to(self.config.target_dir))
            if any(pattern in rel_path for pattern in self.config.excluded_patterns):
                return False
                
            # Check if it's a test file
            is_test = any(str(file_path).lower().endswith(test_pattern.lower()) 
                         for test_pattern in [
                             '_test.', 'test_', '_spec.', 'spec_',
                             '.spec.', '.test.', 'tests.'
                         ])
            if is_test and not self.config.include_tests:
                return False
                
            return True
            
        except Exception as e:
            console.print(f"[yellow]Warning: Error checking file {file_path}: {e}[/yellow]")
            return False

    async def _read_file(self, file_path: Path) -> Optional[str]:
        """Read file content with proper encoding detection."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except UnicodeDecodeError:
            # Try different encodings
            encodings = ['latin-1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                        return await f.read()
                except UnicodeDecodeError:
                    continue
            self._record_failure(file_path, "Unable to detect file encoding")
            return None
        except Exception as e:
            self._record_failure(file_path, f"Error reading file: {str(e)}")
            return None

    def _record_failure(self, file_path: Path, error: str):
        """Record a file processing failure."""
        self.stats['failed_files'] += 1
        self.stats['failed_files_info'].append({
            'file': str(file_path),
            'error': error
        })

    async def _save_results(self, results: List[Dict[str, Any]]):
        """Save processing results to file."""
        try:
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'repository_root': str(self.config.target_dir),
                'total_files': len(results),
                'statistics': self.stats
            }

            # Handle output path resolution
            if self.config.output_file:
                output_path = Path(self.config.output_file)
                # If not absolute, make it relative to repo output directory
                if not output_path.is_absolute():
                    output_path = self.default_output_dir / output_path
            else:
                # Generate default filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                repo_name = self.config.target_dir.name
                output_filename = f"code_context_{repo_name}_{timestamp}.{self.config.output_format}"
                output_path = self.default_output_dir / output_filename

            # Ensure the output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert absolute path to repo-relative path for display
            try:
                relative_path = output_path.relative_to(self.repo_root)
                display_path = f"{self.repo_root.name}/{relative_path}"
            except ValueError:
                # If the path is outside repo, use absolute path
                display_path = str(output_path)

            if self.config.output_format == 'jsonl':
                async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(metadata) + '\n')
                    for result in results:
                        await f.write(json.dumps(result) + '\n')
            else:  # json format
                async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps({
                        'metadata': metadata,
                        'files': results
                    }, indent=2))

            console.print(f"\n[green]Results saved to: {display_path}[/green]")
        except Exception as e:
            raise FileProcessingError(f"Error saving results: {str(e)}")

    def _display_summary(self):
        """Display processing summary."""
        from rich.table import Table
        
        table = Table(title="Processing Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")
        
        # Add statistics
        table.add_row("Files Processed", str(self.stats['processed_files']))
        table.add_row("Files Skipped", str(self.stats['skipped_files']))
        table.add_row("Files Failed", str(self.stats['failed_files']))
        table.add_row("Total Files", str(self.stats['total_files']))
        
        # Add file sizes
        def format_size(size: int) -> str:
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        
        table.add_row("Total Raw Size", format_size(self.stats['total_raw_size']))
        table.add_row("Total Cleaned Size", format_size(self.stats['total_cleaned_size']))
        
        # Add processing time
        table.add_row(
            "Processing Time", 
            f"{self.stats['processing_time']:.2f} seconds"
        )
        
        # Calculate and add size reduction percentage
        if self.stats['total_raw_size'] > 0:
            reduction = (
                1 - self.stats['total_cleaned_size'] / self.stats['total_raw_size']
            ) * 100
            table.add_row("Size Reduction", f"{reduction:.1f}%")
        
        console.print("\n")
        console.print(table)
        console.print("\n")
        
        # Display failures if any
        if self.stats['failed_files'] > 0:
            console.print("[yellow]Failed Files:[/yellow]")
            for fail_info in self.stats['failed_files_info']:
                console.print(
                    f"  [red]• {fail_info['file']}: {fail_info['error']}[/red]"
                )
            console.print("\n")

    @property
    def supported_languages(self) -> set[str]:
        """Get list of supported languages."""
        return self.registry.supported_languages

    @property
    def supported_extensions(self) -> set[str]:
        """Get list of supported file extensions."""
        return self.registry.supported_extensions