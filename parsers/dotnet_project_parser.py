import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from pathlib import Path
import re
import logging

class DotNetProjectParser:
    """Parser for .NET project files (*.csproj, *.fsproj, *.vbproj)"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_project_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a .NET project file and extract relevant information."""
        try:
            tree = ET.parse(str(file_path))
            root = tree.getroot()
            
            result = {
                'project_type': self._determine_project_type(root),
                'target_frameworks': self._get_target_frameworks(root),
                'sdk': self._get_sdk_version(root),
                'packages': self._get_package_references(root),
                'project_references': self._get_project_references(root),
                'properties': self._get_project_properties(root),
                'assembly_info': self._get_assembly_info(root)
            }

            # Parse Directory.Build.props if it exists
            build_props = file_path.parent / 'Directory.Build.props'
            if build_props.exists():
                result['directory_build_props'] = self._parse_directory_build_props(build_props)

            return result
        except Exception as e:
            self.logger.error(f'Error parsing project file {file_path}: {e}')
            return {}

    def _determine_project_type(self, root: ET.Element) -> str:
        """Determine the type of .NET project."""
        sdk = root.get('Sdk', '')
        
        if 'Microsoft.NET.Sdk.Web' in sdk:
            return 'web'
        elif 'Microsoft.NET.Sdk.Worker' in sdk:
            return 'worker'
        elif 'Microsoft.NET.Sdk.BlazorWebAssembly' in sdk:
            return 'blazor-wasm'
        elif 'Microsoft.NET.Sdk.Razor' in sdk:
            return 'razor-library'
        elif 'Microsoft.NET.Sdk.WindowsDesktop' in sdk:
            return 'windows-desktop'
        elif any(self._find_element(root, f".//*[contains(text(), '{text}')]") 
                for text in ['WPF', 'WindowsForms']):
            return 'windows-ui'
        elif self._find_element(root, ".//TestSDK"):
            return 'test'
        else:
            return 'library'

    def _get_target_frameworks(self, root: ET.Element) -> List[str]:
        """Extract target framework information."""
        frameworks = []
        
        # Check for single target framework
        tf_element = self._find_element(root, ".//TargetFramework")
        if tf_element is not None and tf_element.text:
            frameworks.append(tf_element.text)
            
        # Check for multiple target frameworks
        tf_elements = self._find_element(root, ".//TargetFrameworks")
        if tf_elements is not None and tf_elements.text:
            frameworks.extend(tf_elements.text.split(';'))
            
        return sorted(list(set(frameworks)))

    def _get_sdk_version(self, root: ET.Element) -> Optional[str]:
        """Extract SDK version information."""
        sdk = root.get('Sdk', '')
        if sdk:
            return sdk
            
        # Check for SDK version in properties
        sdk_version = self._find_element(root, ".//LangVersion")
        if sdk_version is not None and sdk_version.text:
            return sdk_version.text
            
        return None

    def _get_package_references(self, root: ET.Element) -> List[Dict[str, str]]:
        """Extract NuGet package references."""
        packages = []
        
        for ref in root.findall(".//PackageReference"):
            package = {
                'name': ref.get('Include', ''),
                'version': ref.get('Version', '')
            }
            
            # Check for version range
            version_element = ref.find("Version")
            if version_element is not None and version_element.text:
                package['version'] = version_element.text
                
            # Check for private assets
            private_assets = ref.get('PrivateAssets', '')
            if private_assets:
                package['private_assets'] = private_assets
                
            if package['name']:
                packages.append(package)
                
        return packages

    def _get_project_references(self, root: ET.Element) -> List[str]:
        """Extract project references."""
        references = []
        
        for ref in root.findall(".//ProjectReference"):
            include = ref.get('Include', '')
            if include:
                references.append(include)
                
        return references

    def _get_project_properties(self, root: ET.Element) -> Dict[str, str]:
        """Extract project properties."""
        properties = {}
        
        property_elements = root.findall(".//PropertyGroup/*")
        for prop in property_elements:
            if prop.tag not in ['TargetFramework', 'TargetFrameworks'] and prop.text:
                properties[prop.tag] = prop.text
                
        return properties

    def _get_assembly_info(self, root: ET.Element) -> Dict[str, str]:
        """Extract assembly information."""
        assembly_info = {}
        
        info_elements = [
            'AssemblyTitle',
            'AssemblyDescription',
            'AssemblyConfiguration',
            'AssemblyCompany',
            'AssemblyProduct',
            'AssemblyCopyright',
            'AssemblyTrademark',
            'AssemblyVersion',
            'FileVersion',
            'NeutralLanguage'
        ]
        
        for element_name in info_elements:
            element = self._find_element(root, f".//{element_name}")
            if element is not None and element.text:
                assembly_info[element_name] = element.text
                
        return assembly_info

    def _parse_directory_build_props(self, file_path: Path) -> Dict[str, Any]:
        """Parse Directory.Build.props file."""
        try:
            tree = ET.parse(str(file_path))
            root = tree.getroot()
            
            return {
                'properties': self._get_project_properties(root),
                'packages': self._get_package_references(root)
            }
        except Exception as e:
            self.logger.error(f'Error parsing Directory.Build.props {file_path}: {e}')
            return {}

    def _find_element(self, root: ET.Element, xpath: str) -> Optional[ET.Element]:
        """Safely find an element using XPath."""
        try:
            return root.find(xpath)
        except Exception:
            return None

    def normalize_framework_version(self, framework: str) -> str:
        """Normalize framework version string."""
        framework = framework.lower()
        
        # Handle common framework formats
        if framework.startswith('net'):
            # .NET 5+ or .NET Core
            if re.match(r'net[5-9]\.0|net\d{2}', framework):
                return f'.NET {framework[3:]}'
            # .NET Core
            elif framework.startswith('netcoreapp'):
                return f'.NET Core {framework[10:]}'
            # .NET Framework
            elif framework.startswith('netframework'):
                return f'.NET Framework {framework[12:]}'
            elif re.match(r'net\d{2,4}', framework):
                return f'.NET Framework {framework[3:]}'
        # .NET Standard
        elif framework.startswith('netstandard'):
            return f'.NET Standard {framework[10:]}'
            
        return framework