from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET
from logging_config import setup_logger

class MSBuildParser:
    """Parser for MSBuild property and target files."""

    def __init__(self):
        self.logger = setup_logger(__name__)

    def parse_msbuild_file(self, file_path: Path) -> Dict[str, any]:
        """Parse MSBuild files (.props and .targets)."""
        try:
            tree = ET.parse(str(file_path))
            root = tree.getroot()

            return {
                'properties': self._parse_properties(root),
                'targets': self._parse_targets(root),
                'imports': self._parse_imports(root),
                'item_groups': self._parse_item_groups(root),
                'conditions': self._extract_conditions(root)
            }
        except Exception as e:
            self.logger.error(f'Error parsing MSBuild file {file_path}: {e}')
            return {}

    def _parse_properties(self, root: ET.Element) -> List[Dict[str, str]]:
        """Extract property definitions."""
        properties = []
        
        for prop_group in root.findall(".//PropertyGroup"):
            condition = prop_group.get('Condition', '')
            
            for prop in prop_group:
                if prop.text:
                    properties.append({
                        'name': prop.tag,
                        'value': prop.text.strip(),
                        'condition': condition
                    })
                    
        return properties

    def _parse_targets(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract target definitions."""
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
            
            for task in target.findall(".//*"):
                if task.tag != 'Target':
                    task_info = {
                        'type': task.tag,
                        'attributes': dict(task.attrib)
                    }
                    target_info['tasks'].append(task_info)
                    
            targets.append(target_info)
            
        return targets

    def _parse_imports(self, root: ET.Element) -> List[Dict[str, str]]:
        """Extract file imports."""
        imports = []
        
        for imp in root.findall(".//Import"):
            imports.append({
                'project': imp.get('Project', ''),
                'condition': imp.get('Condition', '')
            })
            
        return imports

    def _parse_item_groups(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract item group definitions."""
        item_groups = []
        
        for group in root.findall(".//ItemGroup"):
            items = []
            condition = group.get('Condition', '')
            
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
                'condition': condition,
                'items': items
            })
            
        return item_groups

    def _extract_conditions(self, root: ET.Element) -> List[str]:
        """Extract all unique conditions."""
        conditions = set()
        
        for elem in root.findall(".//*[@Condition]"):
            condition = elem.get('Condition', '').strip()
            if condition:
                conditions.add(condition)
                
        return sorted(list(conditions))

    def analyze_msbuild_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze MSBuild file and provide summary metrics."""
        try:
            parsed_data = self.parse_msbuild_file(file_path)
            
            return {
                'success': True,
                'metrics': {
                    'property_count': len(parsed_data.get('properties', [])),
                    'target_count': len(parsed_data.get('targets', [])),
                    'import_count': len(parsed_data.get('imports', [])),
                    'item_group_count': len(parsed_data.get('item_groups', [])),
                    'condition_count': len(parsed_data.get('conditions', []))
                },
                'content': parsed_data,
                'file_type': 'msbuild'
            }
        except Exception as e:
            self.logger.error(f'Error analyzing MSBuild file {file_path}: {e}')
            return {
                'success': False,
                'error': str(e)
            }