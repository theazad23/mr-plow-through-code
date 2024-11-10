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
from parsers.file_parser import FileParser
from parsers.file_patterns_config import FilePatterns
from parsers.dotnet_project_parser import DotNetProjectParser
from parsers.msbuild_parser import MSBuildParser

class ContentProcessor:
    """Processes source code files using language-specific handlers."""

    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.registry = CodeHandlerRegistry()
        self.logger = logging.getLogger(__name__)
        
        # Initialize parsers with custom patterns if needed
        custom_patterns = FilePatterns.create_with_gitignore(
            target_dir=config.target_dir,
            additional_ignore_patterns=config.excluded_patterns,
            additional_categories={'custom': list(config.included_extensions)} if config.included_extensions else None
        )
        self.file_parser = FileParser(patterns=custom_patterns)
        self.dotnet_parser = DotNetProjectParser()
        self.msbuild_parser = MSBuildParser()
        
        if config.verbose:
            self.logger.setLevel(logging.DEBUG)
            
        self.repo_name = self.config.target_dir.name
        self.output_dir = Path(__file__).parent.parent / 'output'
        self.output_dir.mkdir(exist_ok=True)
        
        self.config.output_file = self.config.output_file or str(
            self.output_dir / f'{self.repo_name}_code_context.{self.config.output_format}'
        )
        
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
            if not self.file_parser.should_process_file(file_path):
                self.logger.debug(f'Skipping {file_path}: not processable')
                return False
                
            if not self.config.include_tests and self.file_parser.patterns.is_test_file(file_path):
                self.logger.debug(f'Skipping {file_path}: test file')
                return False
                
            if file_path.stat().st_size > self.config.max_file_size:
                self.logger.debug(f'Skipping {file_path}: exceeds size limit')
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
            
            # Get file info from parser
            file_info = self.file_parser.process_file(file_path)
            if not file_info:
                self.stats['skipped_files'] += 1
                return None

            # Get appropriate handler
            handler = self.registry.get_handler_for_file(file_path)
            if not handler:
                self.logger.warning(f'No handler found for {file_path}')
                self.stats['skipped_files'] += 1
                return None

            # Process content
            content = file_info['content']
            cleaned_content = handler.clean_content(content)
            if not cleaned_content.strip():
                self.logger.debug(f'Skipping {file_path}: empty after cleaning')
                self.stats['skipped_files'] += 1
                return None

            # Analyze code
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

            # Update statistics
            file_type = file_path.suffix.lstrip('.')
            raw_size = file_path.stat().st_size
            cleaned_size = len(cleaned_content.encode('utf-8'))
            
            self.stats['total_raw_size'] += raw_size
            self.stats['total_cleaned_size'] += cleaned_size
            self.stats['file_types'][file_type] = self.stats['file_types'].get(file_type, 0) + 1
            self.stats['processed_files'] += 1

            return {
                'path': str(file_path.relative_to(self.config.target_dir)),
                'type': file_type,
                'analysis': analysis,
                'size': cleaned_size,
                'content': cleaned_content,
                'hash': calculate_file_hash(file_path),
                'category': file_info['category'],
                'is_test': file_info['is_test']
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
            files = [f for f in self.config.target_dir.rglob('*') if await self.should_process_file(f)]
            self.stats['total_files'] = len(files)

            results = []
            with Progress() as progress:
                task = progress.add_task('[cyan]Processing files...', total=len(files))
                for file_path in files:
                    result = await self.process_file(file_path)
                    if result:
                        results.append(result)
                    progress.update(task, advance=1)

            self.stats['processing_time'] = asyncio.get_event_loop().time() - start_time
            await self.save_results(results)

            if self.stats['failed_files'] > 0:
                self.logger.error('\nFailed files details:')
                for fail_info in self.stats['failed_files_info']:
                    self.logger.error(f"\nFile: {fail_info['file']}\nError: {fail_info['error']}")

            return self.stats

        except Exception as e:
            self.logger.error(f'Error during processing: {e}')
            raise

    async def save_results(self, results: List[Dict]) -> None:
        """Save processing results to file."""
        try:
            output_path = Path(self.config.output_file)
            if not output_path.is_absolute():
                output_path = self.output_dir / output_path
            self.logger.info(f'Saving results to {output_path}')
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'repository_root': str(self.config.target_dir),
                'total_files': len(results),
                'statistics': self.stats
            }
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if self.config.output_format == 'jsonl':
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(json.dumps(metadata) + '\n')
                    for result in results:
                        f.write(json.dumps(result) + '\n')
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump({'metadata': metadata, 'files': results}, f, indent=2)
            self.logger.info(f'Results saved successfully to {output_path}')
        except Exception as e:
            self.logger.error(f'Error saving results: {e}')
            raise
        
    async def _process_dotnet_project(self, file_path: Path) -> Optional[Dict]:
        """Process .NET project files using DotNetProjectParser"""
        try:
            self.logger.debug(f'Processing .NET project file: {file_path}')
            
            # Parse the project file
            project_info = self.dotnet_parser.parse_project_file(file_path)
            
            # Get associated MSBuild files
            directory_build_props = file_path.parent / 'Directory.Build.props'
            directory_build_targets = file_path.parent / 'Directory.Build.targets'
            
            # Add MSBuild information if available
            if directory_build_props.exists():
                project_info['directory_build_props'] = await self._process_msbuild_file(directory_build_props)
            
            if directory_build_targets.exists():
                project_info['directory_build_targets'] = await self._process_msbuild_file(directory_build_targets)
            
            # Analyze project structure
            source_files = []
            test_files = []
            for item in file_path.parent.rglob('*.cs'):
                rel_path = str(item.relative_to(file_path.parent))
                if any(pattern in rel_path.lower() for pattern in ['test', 'spec']):
                    test_files.append(rel_path)
                else:
                    source_files.append(rel_path)

            analysis = {
                'success': True,
                'project_info': project_info,
                'structure': {
                    'source_files': source_files,
                    'test_files': test_files,
                    'framework_targets': project_info.get('target_frameworks', []),
                    'package_references': project_info.get('packages', []),
                    'project_references': project_info.get('project_references', [])
                },
                'metrics': {
                    'source_file_count': len(source_files),
                    'test_file_count': len(test_files),
                    'package_reference_count': len(project_info.get('packages', [])),
                    'project_reference_count': len(project_info.get('project_references', []))
                }
            }

            return {
                'path': str(file_path.relative_to(self.config.target_dir)),
                'type': 'dotnet-project',
                'analysis': analysis,
                'size': file_path.stat().st_size,
                'content': project_info,
                'hash': calculate_file_hash(file_path)
            }

        except Exception as e:
            self.logger.error(f'Error processing .NET project file {file_path}: {e}')
            return None

    async def _process_msbuild_file(self, file_path: Path) -> Optional[Dict]:
        """Process MSBuild files using MSBuildParser"""
        try:
            self.logger.debug(f'Processing MSBuild file: {file_path}')
            
            # Parse and analyze the MSBuild file
            analysis = self.msbuild_parser.analyze_msbuild_file(file_path)
            
            if not analysis['success']:
                self.logger.error(f'Failed to analyze MSBuild file {file_path}: {analysis.get("error")}')
                return None

            return {
                'path': str(file_path.relative_to(self.config.target_dir)),
                'type': 'msbuild',
                'analysis': analysis,
                'size': file_path.stat().st_size,
                'content': analysis['content'],
                'hash': calculate_file_hash(file_path)
            }

        except Exception as e:
            self.logger.error(f'Error processing MSBuild file {file_path}: {e}')
            return None

    async def _process_solution_file(self, file_path: Path) -> Optional[Dict]:
        """Process .NET solution files with enhanced project analysis"""
        try:
            self.logger.debug(f'Processing solution file: {file_path}')
            content = read_file_safely(file_path, self.logger)
            
            if not content:
                return None

            # Parse solution file
            projects = []
            solution_folders = []
            
            project_pattern = r'Project\("{([^}]+)}"\)\s*=\s*"([^"]+)",\s*"([^"]+)",\s*"{([^}]+)}"'
            
            for match in re.finditer(project_pattern, content):
                project_type_guid, project_name, project_path, project_guid = match.groups()
                
                # Convert relative path to absolute
                project_file = (file_path.parent / project_path).resolve()
                
                if project_type_guid == '2150E333-8FDC-42A3-9474-1A3956D46DE8':
                    # Solution folder
                    solution_folders.append({
                        'name': project_name,
                        'guid': project_guid
                    })
                elif project_file.exists():
                    # Actual project
                    project_info = None
                    if project_file.suffix.lower() in {'.csproj', '.fsproj', '.vbproj'}:
                        project_analysis = await self._process_dotnet_project(project_file)
                        if project_analysis:
                            project_info = project_analysis.get('analysis', {}).get('project_info')
                    
                    projects.append({
                        'name': project_name,
                        'path': project_path,
                        'guid': project_guid,
                        'type': project_file.suffix.lower()[1:],
                        'info': project_info
                    })

            analysis = {
                'success': True,
                'solution_info': {
                    'projects': projects,
                    'solution_folders': solution_folders,
                    'metrics': {
                        'total_projects': len(projects),
                        'solution_folders': len(solution_folders),
                        'project_types': {
                            'csproj': sum(1 for p in projects if p['type'] == 'csproj'),
                            'fsproj': sum(1 for p in projects if p['type'] == 'fsproj'),
                            'vbproj': sum(1 for p in projects if p['type'] == 'vbproj')
                        }
                    }
                }
            }

            return {
                'path': str(file_path.relative_to(self.config.target_dir)),
                'type': 'solution',
                'analysis': analysis,
                'size': file_path.stat().st_size,
                'content': content,
                'hash': calculate_file_hash(file_path)
            }

        except Exception as e:
            self.logger.error(f'Error processing solution file {file_path}: {e}')
            return None