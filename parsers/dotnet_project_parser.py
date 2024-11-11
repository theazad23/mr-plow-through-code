import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import re
from logging_config import setup_logger

class DotNetProjectParser:
    """
    Parser for .NET project files and MSBuild files.
    Handles analysis of .csproj, .fsproj, .vbproj, and related MSBuild files.
    """
    def __init__(self):
        self.logger = setup_logger(__name__)

    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Main entry point for parsing any .NET related file.
        Determines the file type and delegates to appropriate parser.
        """
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            file_type = self._determine_file_type(file_path)
            tree = ET.parse(str(file_path))
            root = tree.getroot()

            if file_type == 'project':
                return self.parse_project_file(file_path, root)
            elif file_type == 'props' or file_type == 'targets':
                return self.parse_msbuild_file(file_path, root)
            else:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")

        except Exception as e:
            self.logger.error(f'Error parsing file {file_path}: {e}')
            return {'success': False, 'error': str(e)}

    def _determine_file_type(self, file_path: Path) -> str:
        """Determines the type of .NET file being parsed."""
        suffix = file_path.suffix.lower()
        name = file_path.name.lower()
        
        if suffix in ['.csproj', '.fsproj', '.vbproj']:
            return 'project'
        elif name == 'directory.build.props' or suffix == '.props':
            return 'props'
        elif name == 'directory.build.targets' or suffix == '.targets':
            return 'targets'
        else:
            return 'unknown'

    def parse_project_file(self, file_path: Path, root: ET.Element) -> Dict[str, Any]:
        """Parses .NET project files (.csproj, .fsproj, .vbproj)"""
        try:
            result = {
                'success': True,
                'project_type': self._determine_project_type(root),
                'target_frameworks': self._get_target_frameworks(root),
                'sdk': self._get_sdk_version(root),
                'packages': self._get_package_references(root),
                'project_references': self._get_project_references(root),
                'properties': self._get_project_properties(root),
                'assembly_info': self._get_assembly_info(root)
            }

            # Parse related build files
            props_path = file_path.parent / 'Directory.Build.props'
            targets_path = file_path.parent / 'Directory.Build.targets'

            if props_path.exists():
                result['directory_build_props'] = self.parse_file(props_path)
            if targets_path.exists():
                result['directory_build_targets'] = self.parse_file(targets_path)

            return result

        except Exception as e:
            self.logger.error(f'Error parsing project file {file_path}: {e}')
            return {'success': False, 'error': str(e)}

    def parse_msbuild_file(self, file_path: Path, root: ET.Element) -> Dict[str, Any]:
        """Parses MSBuild files (.props, .targets)"""
        try:
            return {
                'success': True,
                'file_type': 'msbuild',
                'properties': self._get_project_properties(root),
                'targets': self._parse_targets(root),
                'imports': self._parse_imports(root),
                'item_groups': self._parse_item_groups(root),
                'conditions': self._extract_conditions(root),
                'metrics': {
                    'property_count': len(root.findall('.//PropertyGroup/*')),
                    'target_count': len(root.findall('.//Target')),
                    'import_count': len(root.findall('.//Import')),
                    'item_group_count': len(root.findall('.//ItemGroup'))
                }
            }

        except Exception as e:
            self.logger.error(f'Error parsing MSBuild file {file_path}: {e}')
            return {'success': False, 'error': str(e)}

    def _determine_project_type(self, root: ET.Element) -> str:
        """Determines the type of .NET project."""
        sdk = root.get('Sdk', '')
        
        sdk_mapping = {
            'Microsoft.NET.Sdk.Web': 'web',
            'Microsoft.NET.Sdk.Worker': 'worker',
            'Microsoft.NET.Sdk.BlazorWebAssembly': 'blazor-wasm',
            'Microsoft.NET.Sdk.Razor': 'razor-library',
            'Microsoft.NET.Sdk.WindowsDesktop': 'windows-desktop'
        }

        for sdk_name, project_type in sdk_mapping.items():
            if sdk_name in sdk:
                return project_type

        # Check for specific patterns
        if any(self._find_element(root, f".//*[contains(text(), '{text}')]") 
               for text in ['WPF', 'WindowsForms']):
            return 'windows-ui'
        elif self._find_element(root, ".//TestSDK"):
            return 'test'

        return 'library'

    def _get_target_frameworks(self, root: ET.Element) -> List[str]:
        """Gets target framework information from the project."""
        frameworks = []
        
        # Single framework
        tf_element = self._find_element(root, ".//TargetFramework")
        if tf_element is not None and tf_element.text:
            frameworks.append(tf_element.text)

        # Multiple frameworks
        tf_elements = self._find_element(root, ".//TargetFrameworks")
        if tf_elements is not None and tf_elements.text:
            frameworks.extend(tf_elements.text.split(';'))

        return [self.normalize_framework_version(fw) for fw in set(frameworks)]

    def _get_package_references(self, root: ET.Element) -> List[Dict[str, str]]:
        """Extracts package references from the project."""
        packages = []
        for ref in root.findall(".//PackageReference"):
            package = {
                'name': ref.get('Include', ''),
                'version': ref.get('Version', '')
            }
            
            # Check for version element
            version_element = ref.find("Version")
            if version_element is not None and version_element.text:
                package['version'] = version_element.text

            # Additional metadata
            for metadata in ref:
                if metadata.tag != 'Version':
                    package[metadata.tag.lower()] = metadata.text

            if package['name']:
                packages.append(package)

        return packages

    def _parse_targets(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Parses MSBuild targets."""
        targets = []
        for target in root.findall(".//Target"):
            target_info = {
                'name': target.get('Name', ''),
                'depends_on': target.get('DependsOnTargets', '').split(';'),
                'inputs': target.get('Inputs', ''),
                'outputs': target.get('Outputs', ''),
                'condition': target.get('Condition', ''),
                'tasks': []
            }

            # Parse tasks within target
            for task in target.findall(".//*"):
                if task.tag != 'Target':
                    target_info['tasks'].append({
                        'type': task.tag,
                        'attributes': dict(task.attrib),
                        'content': task.text if task.text and task.text.strip() else None
                    })

            targets.append(target_info)
        return targets

    def _parse_imports(self, root: ET.Element) -> List[Dict[str, str]]:
        """Parses MSBuild imports."""
        return [{
            'project': imp.get('Project', ''),
            'condition': imp.get('Condition', ''),
            'sdk': imp.get('Sdk', '')
        } for imp in root.findall(".//Import")]

    def _parse_item_groups(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Parses MSBuild item groups."""
        item_groups = []
        for group in root.findall(".//ItemGroup"):
            items = []
            for item in group:
                item_info = {
                    'type': item.tag,
                    'include': item.get('Include', ''),
                    'exclude': item.get('Exclude', ''),
                    'remove': item.get('Remove', ''),
                    'update': item.get('Update', ''),
                    'metadata': {}
                }
                
                for metadata in item:
                    if metadata.text:
                        item_info['metadata'][metadata.tag] = metadata.text.strip()
                
                items.append(item_info)

            item_groups.append({
                'condition': group.get('Condition', ''),
                'items': items
            })
        
        return item_groups

    def _extract_conditions(self, root: ET.Element) -> List[str]:
        """Extracts and normalizes all conditions from the file."""
        conditions = set()
        for elem in root.findall(".//*[@Condition]"):
            condition = elem.get('Condition', '').strip()
            if condition:
                conditions.add(condition)
        return sorted(list(conditions))

    def _get_project_properties(self, root: ET.Element) -> Dict[str, str]:
        """Gets all project properties."""
        properties = {}
        for prop in root.findall(".//PropertyGroup/*"):
            if prop.tag not in ['TargetFramework', 'TargetFrameworks'] and prop.text:
                properties[prop.tag] = prop.text.strip()
        return properties

    def _get_assembly_info(self, root: ET.Element) -> Dict[str, str]:
        """Extracts assembly information."""
        assembly_info = {}
        info_elements = [
            'AssemblyTitle', 'AssemblyDescription', 'AssemblyConfiguration',
            'AssemblyCompany', 'AssemblyProduct', 'AssemblyCopyright',
            'AssemblyTrademark', 'AssemblyVersion', 'FileVersion',
            'NeutralLanguage'
        ]

        for element_name in info_elements:
            element = self._find_element(root, f".//{element_name}")
            if element is not None and element.text:
                assembly_info[element_name] = element.text.strip()

        return assembly_info

    def _find_element(self, root: ET.Element, xpath: str) -> Optional[ET.Element]:
        """Safely finds an element using XPath."""
        try:
            return root.find(xpath)
        except Exception as e:
            self.logger.debug(f"Error finding element with xpath {xpath}: {e}")
            return None

    def _get_sdk_version(self, root: ET.Element) -> Optional[str]:
        """Gets the SDK version information."""
        sdk = root.get('Sdk', '')
        if sdk:
            return sdk
        
        sdk_version = self._find_element(root, ".//LangVersion")
        if sdk_version is not None and sdk_version.text:
            return sdk_version.text
        
        return None

    def _get_project_references(self, root: ET.Element) -> List[str]:
        """Gets project references."""
        return [ref.get('Include', '') for ref in root.findall(".//ProjectReference") 
                if ref.get('Include')]

    def normalize_framework_version(self, framework: str) -> str:
        """Normalizes the framework version string."""
        framework = framework.lower()
        
        if framework.startswith('net'):
            if re.match(r'net[5-9]\.0|net\d{2}', framework):
                return f'.NET {framework[3:]}'
            elif framework.startswith('netcoreapp'):
                return f'.NET Core {framework[10:]}'
            elif framework.startswith('netframework'):
                return f'.NET Framework {framework[12:]}'
            elif re.match(r'net\d{2,4}', framework):
                return f'.NET Framework {framework[3:]}'
        elif framework.startswith('netstandard'):
            return f'.NET Standard {framework[10:]}'
        
        return framework