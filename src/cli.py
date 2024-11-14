# src/cli.py
import asyncio
import argparse
from pathlib import Path
from rich.console import Console
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.config import ProcessorConfig
from src.core.processor import CodeContextProcessor

console = Console()

def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate code context for LLM processing'
    )
    parser.add_argument(
        'path',
        type=str,
        help='Path to code directory'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file path'
    )
    parser.add_argument(
        '-f', '--format',
        choices=['jsonl', 'json'],
        default='jsonl',
        help='Output format (default: jsonl)'
    )
    parser.add_argument(
        '--include-tests',
        action='store_true',
        help='Include test files in analysis'
    )
    parser.add_argument(
        '--max-size',
        type=int,
        default=1024 * 1024,
        help='Maximum file size in bytes (default: 1MB)'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    return parser.parse_args()

async def main():
    try:
        args = parse_args()
        path = Path(args.path)
        if not path.exists() or not path.is_dir():
            console.print(f'[red]Error:[/red] Invalid directory: {path}')
            return 1

        # Add debug output
        console.print(f"[blue]Debug: Processing directory: {path}[/blue]")
        console.print(f"[blue]Debug: Python path: {sys.path}[/blue]")

        config = ProcessorConfig(
            target_dir=path,
            output_file=args.output,
            output_format=args.format,
            include_tests=args.include_tests,
            max_file_size=args.max_size
        )
        processor = CodeContextProcessor(config)
        
        # Add debug output for supported extensions
        console.print(f"[blue]Debug: Supported extensions: {processor.supported_extensions}[/blue]")
        
        await processor.process_directory()
        return 0
    except KeyboardInterrupt:
        console.print('\n[yellow]Process interrupted by user[/yellow]')
        return 1
    except Exception as e:
        console.print(f'\n[red]Error:[/red] {str(e)}')
        if args.verbose:
            console.print_exception()
        return 1

if __name__ == '__main__':
    if asyncio.get_event_loop().is_closed():
        asyncio.set_event_loop(asyncio.new_event_loop())
    exit_code = asyncio.run(main())
    exit(exit_code)