"""
Payload Scaler Module
Core scaling logic and payload transformations
"""

import copy
import uuid
import re
from datetime import datetime
from typing import Dict, List, Any, Set, Optional


class PayloadScaler:
    """Handles payload scaling and transformation logic"""
    
    def __init__(self, logger):
        self.logger = logger
        
        # Entities that are auto-linked to service count (scales automatically with services)
        self.auto_linked_entities = {
            'substrate_definition_list',  # Same count as services
            'package_definition_list',  # Same count as services
            'deployment_create_list',  # Same count as services
        }
        
    def is_id_field(self, field_name: str) -> bool:
        """Check if a field name represents an ID field"""
        id_patterns = [
            r'.*_?id$', r'.*_?uuid$', r'.*_?guid$', r'.*_?key$',
            r'^id$', r'^uuid$', r'^guid$', r'^key$'
        ]
        return any(re.match(pattern, field_name, re.IGNORECASE) for pattern in id_patterns)
        
    def is_uuid_like(self, value: Any) -> bool:
        """Check if a value looks like a UUID"""
        if not isinstance(value, str):
            return False
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(uuid_pattern, value, re.IGNORECASE))
        
    def generate_new_id(self, original_value: Any, index: int) -> Any:
        """Generate a new ID based on the original value and index"""
        if self.is_uuid_like(original_value):
            return str(uuid.uuid4())
        elif isinstance(original_value, int):
            return original_value + index
        elif isinstance(original_value, str):
            if original_value.isdigit():
                return str(int(original_value) + index)
            else:
                return f"{original_value}_{index + 1}"
        else:
            return f"{original_value}_{index + 1}"
            
    def collect_all_id_values(self, data: Any, path: str = "", id_values: Dict[str, Set[Any]] = None) -> Dict[str, Set[Any]]:
        """Collect all ID values from the payload"""
        if id_values is None:
            id_values = {}
            
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                if self.is_id_field(key) and value is not None:
                    if current_path not in id_values:
                        id_values[current_path] = set()
                    id_values[current_path].add(value)
                else:
                    self.collect_all_id_values(value, current_path, id_values)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                self.collect_all_id_values(item, current_path, id_values)
                
        return id_values
        
    def find_references(self, data: Any, id_values: Dict[str, Set[Any]], path: str = "", references: Dict[str, List[str]] = None) -> Dict[str, List[str]]:
        """Find all references to ID values in the payload"""
        if references is None:
            references = {}
            
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check if this value references any known ID
                if value is not None:
                    for id_path, id_set in id_values.items():
                        if value in id_set and current_path != id_path:
                            if id_path not in references:
                                references[id_path] = []
                            references[id_path].append(current_path)
                            
                self.find_references(value, id_values, current_path, references)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                self.find_references(item, id_values, current_path, references)
                
        return references
        
    def get_non_scalable_entities(self, api_type: str = 'blueprint') -> set:
        """Get entities that should not be scaled"""
        if api_type == 'blueprint':
            return {
                'spec.resources.credential_definition_list',
                'spec.resources.default_credential_local_reference'
            }
        return set()
        
    def find_entities_in_payload(self, data: Any, path: str = "", entities: Dict[str, Any] = None, api_type: str = 'blueprint') -> Dict[str, Any]:
        """Find all scalable entities (arrays) in the payload"""
        if entities is None:
            entities = {}
            
        non_scalable = self.get_non_scalable_entities(api_type)
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, list) and len(value) > 0:
                    # Skip non-scalable entities
                    if current_path in non_scalable:
                        continue
                        
                    # This is a potential entity to scale
                    entities[current_path] = {
                        'current_count': len(value),
                        'sample_item': value[0] if value else None,
                        'full_path': current_path
                    }
                    
                # Recursively search in nested structures
                self.find_entities_in_payload(value, current_path, entities, api_type)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                self.find_entities_in_payload(item, current_path, entities, api_type)
                
        return entities
        
    def calculate_entity_counts_from_user_input(self, user_input: Dict[str, int]) -> Dict[str, int]:
        """Calculate full entity_counts from simplified user input"""
        services = user_input.get('services', 1)
        app_profiles = user_input.get('app_profiles', 1)
        credentials = user_input.get('credentials', 1)
        
        # Auto-calculate based on hardcoded rules
        packages = app_profiles * services  # Updated rule: Packages = App Profiles × Services
        deployments_per_profile = services
        substrates = app_profiles * services
        
        self.logger.info(f"DEBUG: User input - Services: {services}, App Profiles: {app_profiles}, Credentials: {credentials}")
        self.logger.info(f"DEBUG: Auto-calculated - Packages: {packages}, Deployments per Profile: {deployments_per_profile}, Substrates: {substrates}")
        
        # Build full entity_counts structure
        entity_counts = {
            'spec.resources.app_profile_list': app_profiles,
            'spec.resources.app_profile_list.deployment_create_list': 1,  # Will be auto-adjusted to services count
            'spec.resources.service_definition_list': services,
            'spec.resources.substrate_definition_list': substrates,
            'spec.resources.package_definition_list': packages,
            'spec.resources.credential_definition_list': credentials,
            'options.install_runbook.task_definition_list': 1,
            'options.uninstall_runbook.task_definition_list': 1
        }
        
        self.logger.info(f"DEBUG: Generated entity_counts: {entity_counts}")
        return entity_counts
        
    def process_user_input_and_generate_payload(self, user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process user input and generate payload"""
        self.logger.info(f"DEBUG: Processing user input: {user_input}")
        
        # Check if this is simplified user input
        if 'services' in user_input or 'app_profiles' in user_input or 'credentials' in user_input:
            self.logger.info("DEBUG: Detected simplified user input format")
            
            # Extract simplified input
            simplified_input = {
                'services': user_input.get('services', 1),
                'app_profiles': user_input.get('app_profiles', 1), 
                'credentials': user_input.get('credentials', 1)
            }
            
            # Calculate full entity_counts
            entity_counts = self.calculate_entity_counts_from_user_input(simplified_input)
            
            # Create full request structure
            processed_request = {
                'api_url': user_input.get('api_url', 'blueprint'),
                'entity_counts': entity_counts
            }
            
            self.logger.info(f"DEBUG: Converted simplified input to full request: {processed_request}")
            return processed_request
        else:
            self.logger.info("DEBUG: Using existing full entity_counts format")
            return user_input
            
    def scale_payload(self, data: Any, entity_counts: Dict[str, int], path: str = "") -> Any:
        """Scale payload based on entity counts"""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, list) and current_path in entity_counts:
                    target_count = entity_counts[current_path]
                    if len(value) > 0 and target_count > 0:
                        # Scale the array
                        template_item = value[0]
                        scaled_array = []
                        for i in range(target_count):
                            new_item = copy.deepcopy(template_item)
                            # Regenerate IDs in the new item
                            new_item = self.regenerate_all_ids_in_object(new_item, i, {}, current_path)
                            scaled_array.append(new_item)
                        result[key] = scaled_array
                    else:
                        result[key] = value
                else:
                    result[key] = self.scale_payload(value, entity_counts, current_path)
            return result
        elif isinstance(data, list):
            return [self.scale_payload(item, entity_counts, f"{path}[{i}]") for i, item in enumerate(data)]
        else:
            return data
            
    def regenerate_all_ids_in_object(self, obj: Any, index: int, id_mapping: Dict, base_path: str) -> Any:
        """Regenerate all ID fields in an object"""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if self.is_id_field(key) and value is not None:
                    # Generate new ID
                    new_id = self.generate_new_id(value, index)
                    result[key] = new_id
                    
                    # Track mapping
                    full_path = f"{base_path}.{key}"
                    if full_path not in id_mapping:
                        id_mapping[full_path] = {}
                    id_mapping[full_path][value] = new_id
                else:
                    result[key] = self.regenerate_all_ids_in_object(value, index, id_mapping, f"{base_path}.{key}")
            return result
        elif isinstance(obj, list):
            return [self.regenerate_all_ids_in_object(item, index, id_mapping, f"{base_path}[{i}]") for i, item in enumerate(obj)]
        else:
            return obj
            
    def add_name_suffix_to_entities(self, data: Any, entity_counts: Dict[str, int]) -> Any:
        """Add numeric suffixes to entity names"""
        def add_suffix_at_path(obj, remaining_parts, indices=None):
            if indices is None:
                indices = {}
                
            if not remaining_parts:
                return obj
                
            if isinstance(obj, dict):
                part = remaining_parts[0]
                if part in obj:
                    if len(remaining_parts) == 1:
                        # This is the target array
                        if isinstance(obj[part], list):
                            for i, item in enumerate(obj[part]):
                                if isinstance(item, dict) and 'name' in item:
                                    original_name = item['name']
                                    if not original_name.endswith(f'_{i + 1}'):
                                        item['name'] = f"{original_name}_{i + 1}"
                    else:
                        obj[part] = add_suffix_at_path(obj[part], remaining_parts[1:], indices)
            elif isinstance(obj, list):
                return [add_suffix_at_path(item, remaining_parts, indices) for item in obj]
                
            return obj
            
        result = copy.deepcopy(data)
        for entity_path in entity_counts.keys():
            parts = entity_path.split('.')
            result = add_suffix_at_path(result, parts)
            
        return result
        
    def update_spec_name(self, data: Any) -> Any:
        """Update the spec name with timestamp"""
        if isinstance(data, dict) and 'spec' in data and 'name' in data['spec']:
            original_name = data['spec']['name']
            
            # Check if name already has a timestamp pattern (avoid duplication)
            timestamp_pattern = r'_\d{8}_\d{6}$'
            if re.search(timestamp_pattern, original_name):
                # Name already has timestamp, don't modify it
                self.logger.info(f"Spec name already has timestamp: {original_name}")
                return data
            
            # Add scaled prefix and timestamp for names without timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data['spec']['name'] = f"scaled_{original_name}_{timestamp}"
        return data
        
    def update_metadata_uuid(self, data: Any) -> Any:
        """Update metadata UUID"""
        if isinstance(data, dict) and 'metadata' in data and isinstance(data['metadata'], dict):
            if 'uuid' in data['metadata']:
                data['metadata']['uuid'] = str(uuid.uuid4())
        return data
        
    def regenerate_all_entity_uuids(self, data: Any) -> Any:
        """Regenerate all entity UUIDs in the payload"""
        uuid_mapping = {}
        
        def get_new_uuid(old_uuid: str) -> str:
            if old_uuid not in uuid_mapping:
                uuid_mapping[old_uuid] = str(uuid.uuid4())
            return uuid_mapping[old_uuid]
            
        def regenerate_all_uuids(obj: Any) -> Any:
            if isinstance(obj, dict):
                result = {}
                for key, value in obj.items():
                    if key == 'uuid' and isinstance(value, str) and self.is_uuid_like(value):
                        result[key] = get_new_uuid(value)
                    else:
                        result[key] = regenerate_all_uuids(value)
                return result
            elif isinstance(obj, list):
                return [regenerate_all_uuids(item) for item in obj]
            else:
                return obj
        
        # Regenerate all UUIDs first
        result = regenerate_all_uuids(data)
        
        # Fix client_attrs to use new deployment UUIDs
        if isinstance(result, dict) and 'spec' in result:
            resources = result.get('spec', {}).get('resources', {})
            if 'client_attrs' in resources and 'app_profile_list' in resources:
                # Collect all current deployment UUIDs
                current_deployment_uuids = []
                for profile in resources.get('app_profile_list', []):
                    for deployment in profile.get('deployment_create_list', []):
                        if 'uuid' in deployment:
                            current_deployment_uuids.append(deployment['uuid'])
                
                # Get old client_attrs keys (these are the old deployment UUIDs)
                old_client_attrs = resources['client_attrs']
                old_deployment_uuids = list(old_client_attrs.keys())
                
                # If we have the same number of deployments, map old to new
                if len(current_deployment_uuids) == len(old_deployment_uuids):
                    new_client_attrs = {}
                    for i, new_uuid in enumerate(current_deployment_uuids):
                        if i < len(old_deployment_uuids):
                            old_uuid = old_deployment_uuids[i]
                            # Copy the position from old to new UUID
                            new_client_attrs[new_uuid] = old_client_attrs[old_uuid]
                    
                    resources['client_attrs'] = new_client_attrs
                    self.logger.info(f"Updated client_attrs with {len(new_client_attrs)} new deployment UUIDs")
                
        return result
