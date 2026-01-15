from flask import Flask, render_template, request, jsonify, Response
import json
import copy
import uuid
import re
import os
import requests
from urllib.parse import urlparse
from typing import Dict, List, Any, Set
from requests.auth import HTTPBasicAuth
import logging
import sys
from datetime import datetime
import glob
import shutil

app = Flask(__name__)

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging - Create new log file on each restart
log_filename = os.path.join(LOGS_DIR, f'payload_scaler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger for this application
logger = logging.getLogger('payload_scaler')
logger.info("="*80)
logger.info("PAYLOAD SCALER APPLICATION STARTING")
logger.info("="*80)

# ============================================================================
# API LOGGING CONFIGURATION
# ============================================================================

# Create API logs directory structure
API_LOGS_DIR = os.path.join(os.path.dirname(__file__), 'api_logs')
os.makedirs(API_LOGS_DIR, exist_ok=True)

# API logging configuration
MAX_API_LOGS_PER_ENDPOINT = 10  # FIFO limit

def ensure_api_log_dir(api_name):
    """Ensure API log directory exists for the given API name"""
    api_dir = os.path.join(API_LOGS_DIR, api_name)
    os.makedirs(api_dir, exist_ok=True)
    return api_dir

def manage_api_log_fifo(api_dir, max_files=MAX_API_LOGS_PER_ENDPOINT):
    """Manage FIFO for API log files - keep only the latest max_files"""
    try:
        # Get all JSON files in the directory
        json_files = glob.glob(os.path.join(api_dir, '*.json'))
        if len(json_files) >= max_files:
            # Sort by modification time (oldest first)
            json_files.sort(key=os.path.getmtime)
            # Remove oldest files to make room for new ones
            files_to_remove = len(json_files) - max_files + 1
            for i in range(files_to_remove):
                try:
                    os.remove(json_files[i])
                    logger.info(f"Removed old API log file: {json_files[i]}")
                except Exception as e:
                    logger.error(f"Error removing old API log file {json_files[i]}: {e}")
    except Exception as e:
        logger.error(f"Error managing FIFO for {api_dir}: {e}")

def log_api_request_response(api_name, endpoint, method, request_data=None, response_data=None, status_code=None, error=None):
    """Log API request and response with FIFO management"""
    try:
        # Ensure directory exists
        api_dir = ensure_api_log_dir(api_name)
        
        # Manage FIFO before adding new log
        manage_api_log_fifo(api_dir)
        
        # Create log entry
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "api_name": api_name,
            "endpoint": endpoint,
            "method": method,
            "request_data": request_data,
            "response_data": response_data,
            "status_code": status_code,
            "error": error
        }
        
        # Write to file
        log_filename = f"{timestamp}_{method.lower()}_{api_name}.json"
        log_filepath = os.path.join(api_dir, log_filename)
        
        with open(log_filepath, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, indent=2, ensure_ascii=False, default=str)
        
        # Log to main logger
        logger.info(f"API {method} {endpoint} - Status: {status_code} - Logged to: {log_filepath}")
        
    except Exception as e:
        logger.error(f"Error logging API request/response for {api_name}: {e}")

# Directory structure
BASE_DIR = os.path.dirname(__file__)
RULES_DIR = os.path.join(BASE_DIR, 'rules')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates_store')
HISTORY_DIR = os.path.join(BASE_DIR, 'history')
API_RULES_FILE = os.path.join(BASE_DIR, 'api_rules.json')  # Rules by API URL

# Create necessary directories
os.makedirs(HISTORY_DIR, exist_ok=True)

# Supported API types
API_TYPES = ['blueprint', 'app', 'runbook']

# Default action values (cannot be removed, only added to)
DEFAULT_ACTION_VALUES = [
    "action_create",
    "action_delete",
    "action_start",
    "action_stop",
    "action_restart"
]

# ============================================================================
# STORAGE FUNCTIONS - Rules are API-centric, entity counts are NEVER persisted
# ============================================================================

def get_rules_path(api_type: str) -> str:
    """Get the rules directory path for an API type."""
    return os.path.join(RULES_DIR, api_type)

def load_default_rules(api_type: str) -> Dict[str, Any]:
    """Load default rules for an API type."""
    rules_file = os.path.join(get_rules_path(api_type), 'default_rules.json')
    if os.path.exists(rules_file):
        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if 'default_rules' not in data:
                    data['default_rules'] = []
                
                # Convert cross_entity_mappings to reference_mapping rules
                for ref_map in data.get('cross_entity_mappings', []):
                    source = ref_map.get('source', '')
                    targets = ref_map.get('targets', [])
                    target = ref_map.get('target', '')
                    mapping_type = ref_map.get('mapping_type', 'one_to_one')
                    
                    # Handle single target
                    if target and not targets:
                        targets = [target]
                    
                    for tgt in targets:
                        rule = {
                            'type': 'reference_mapping',
                            'source_path': source,
                            'target_path': tgt,
                            'mapping_type': mapping_type,
                            'description': ref_map.get('description', ''),
                            'is_default': True
                        }
                        data['default_rules'].append(rule)
                
                # Legacy support: Convert old reference_mappings format
                for ref_map in data.get('reference_mappings', []):
                    rule = {
                        'type': 'reference_mapping',
                        'source_path': ref_map.get('source', ''),
                        'target_path': ref_map.get('target', ''),
                        'mapping_type': ref_map.get('mapping_type', 'one_to_one'),
                        'description': ref_map.get('description', ''),
                        'is_default': True
                    }
                    data['default_rules'].append(rule)
                
                return data
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def load_api_rules() -> Dict[str, Any]:
    """Load saved API rules from file (API URL -> rules mapping)."""
    if os.path.exists(API_RULES_FILE):
        try:
            with open(API_RULES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_api_rules(rules_data: Dict[str, Any]) -> None:
    """Save API rules to file."""
    with open(API_RULES_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules_data, f, indent=2)

def save_api_rule_set(api_url: str, api_type: str, rules: List[Dict], 
                       payload_template: Any = None, scalable_entities: List[str] = None,
                       task_execution: str = 'parallel') -> None:
    """
    Save rules for a specific API URL.
    NOTE: Entity counts are NOT saved - only rules!
    """
    all_rules = load_api_rules()
    all_rules[api_url] = {
        'api_type': api_type,
        'rules': rules,
        'scalable_entities': scalable_entities or [],
        'task_execution': task_execution,  # For runbooks: 'parallel' or 'series'
        'created_at': str(uuid.uuid4())[:8]
    }
    
    # Optionally store payload template for reference
    if payload_template:
        template_dir = os.path.join(TEMPLATES_DIR, api_type)
        os.makedirs(template_dir, exist_ok=True)
        
        # Create a safe filename from API URL
        safe_name = re.sub(r'[^\w\-]', '_', api_url)[:50]
        template_file = os.path.join(template_dir, f'{safe_name}.json')
        
        with open(template_file, 'w', encoding='utf-8') as f:
            json.dump({
                'api_url': api_url,
                'api_type': api_type,
                'payload_template': payload_template
            }, f, indent=2)
        
        all_rules[api_url]['has_template'] = True
        all_rules[api_url]['template_file'] = template_file
    
    save_api_rules(all_rules)

def get_api_rule_set(api_url: str) -> Dict[str, Any]:
    """Get rules for a specific API URL."""
    all_rules = load_api_rules()
    # Try exact match first
    if api_url in all_rules:
        return all_rules[api_url]
    # Try with leading slash (Flask's path converter may strip it)
    if not api_url.startswith('/') and f'/{api_url}' in all_rules:
        return all_rules[f'/{api_url}']
    # Try without leading slash
    if api_url.startswith('/') and api_url[1:] in all_rules:
        return all_rules[api_url[1:]]
    return {}

def delete_api_rule_set(api_url: str) -> bool:
    """Delete rules for a specific API URL."""
    all_rules = load_api_rules()
    
    # Find the actual key (handle leading slash variations)
    actual_key = None
    if api_url in all_rules:
        actual_key = api_url
    elif not api_url.startswith('/') and f'/{api_url}' in all_rules:
        actual_key = f'/{api_url}'
    elif api_url.startswith('/') and api_url[1:] in all_rules:
        actual_key = api_url[1:]
    
    if actual_key:
        # Also delete template file if exists
        rule_data = all_rules[actual_key]
        if rule_data.get('template_file') and os.path.exists(rule_data['template_file']):
            try:
                os.remove(rule_data['template_file'])
            except OSError:
                pass
        
        del all_rules[actual_key]
        save_api_rules(all_rules)
        return True
    return False

def load_payload_template(api_url: str) -> Any:
    """Load payload template for an API URL."""
    rule_data = get_api_rule_set(api_url)
    template_file = rule_data.get('template_file')
    
    if template_file and os.path.exists(template_file):
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('payload_template')
        except (json.JSONDecodeError, IOError):
            pass
    return None

# ============================================================================
# HISTORY MANAGEMENT
# ============================================================================

def get_history_file(entity_name: str) -> str:
    """Get the history file path for an entity."""
    safe_name = re.sub(r'[^\w\-]', '_', entity_name)[:50]
    return os.path.join(HISTORY_DIR, f'{safe_name}_history.json')

def load_entity_history(entity_name: str) -> List[Dict]:
    """Load history for an entity."""
    history_file = get_history_file(entity_name)
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []

def save_entity_history(entity_name: str, history: List[Dict]) -> None:
    """Save history for an entity."""
    history_file = get_history_file(entity_name)
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)

def get_response_history_file_path(api_url: str) -> str:
    """Get the path to the response history file for an API URL."""
    safe_name = re.sub(r'[^\w\-]', '_', api_url)[:50]
    return os.path.join(HISTORY_DIR, f'{safe_name}_responses.json')

def save_response_history(api_url: str, response_payload: Any, entity_counts: Dict[str, int]) -> None:
    """
    Save the last 5 response payloads for an entity.
    Each response includes the payload and the entity_counts used to generate it.
    """
    history_file = get_response_history_file_path(api_url)
    
    # Load existing history
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = []
    
    # Add new response
    new_entry = {
        'timestamp': str(uuid.uuid4())[:8],  # Simple timestamp identifier
        'entity_counts': entity_counts,
        'response_payload': response_payload
    }
    
    history.insert(0, new_entry)  # Add to beginning
    
    # Keep only last 5
    history = history[:5]
    
    # Save back
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
    except IOError:
        pass  # Silently fail if can't write

def get_response_history(api_url: str) -> List[Dict[str, Any]]:
    """Get the last 5 response payloads for an entity."""
    history_file = get_response_history_file_path(api_url)
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    return []

def get_api_request_response_file_path(api_path: str) -> str:
    """Get the path to the API request/response history file."""
    safe_name = re.sub(r'[^\w\-]', '_', api_path)[:50]
    return os.path.join(HISTORY_DIR, f'api_{safe_name}_requests.json')

def save_api_request_response(api_path: str, method: str, request_data: Any, response_data: Any, status_code: int = 200) -> None:
    """
    Save the last 5 API requests and responses for an endpoint.
    Each entry includes request method, request data, response data, and status code.
    """
    # Use new comprehensive API logging system
    api_name = api_path.replace('/', '_').replace(':', '_').strip('_')
    log_api_request_response(
        api_name=f"scalar_{api_name}",
        endpoint=api_path,
        method=method,
        request_data=request_data,
        response_data=response_data,
        status_code=status_code
    )
    
    # Keep existing history system for backward compatibility
    history_file = get_api_request_response_file_path(api_path)
    
    # Load existing history
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = []
    
    # Add new entry
    new_entry = {
        'timestamp': str(uuid.uuid4())[:8],  # Simple timestamp identifier
        'method': method,
        'request': request_data,
        'response': response_data,
        'status_code': status_code
    }
    
    history.insert(0, new_entry)  # Add to beginning
    
    # Keep only last 5
    history = history[:5]
    
    # Save back
    try:
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
    except IOError:
        pass  # Silently fail if can't write

def get_api_request_response_history(api_path: str) -> List[Dict[str, Any]]:
    """Get the last 5 API requests and responses for an endpoint."""
    history_file = get_api_request_response_file_path(api_path)
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    return []

def add_to_history(entity_name: str, rule_data: Dict, payload_template: Any = None) -> None:
    """Add current version to history before updating."""
    import datetime
    
    history = load_entity_history(entity_name)
    
    # Create history entry
    history_entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'version': len(history) + 1,
        'api_type': rule_data.get('api_type', 'blueprint'),
        'rules': rule_data.get('rules', []),
        'scalable_entities': rule_data.get('scalable_entities', []),
        'task_execution': rule_data.get('task_execution', 'parallel'),
        'rules_count': len(rule_data.get('rules', [])),
        'entities_count': len(rule_data.get('scalable_entities', []))
    }
    
    # Include payload template if available
    if payload_template:
        history_entry['payload_template'] = payload_template
    
    # Add to beginning of history (most recent first)
    history.insert(0, history_entry)
    
    # Keep only last 20 versions
    history = history[:20]
    
    save_entity_history(entity_name, history)

def get_history_version(entity_name: str, version_index: int) -> Dict:
    """Get a specific version from history."""
    history = load_entity_history(entity_name)
    if 0 <= version_index < len(history):
        return history[version_index]
    return {}

def restore_from_history(entity_name: str, version_index: int) -> bool:
    """Restore an entity from a history version."""
    history = load_entity_history(entity_name)
    
    if not (0 <= version_index < len(history)):
        return False
    
    version_to_restore = history[version_index]
    
    # First, save current version to history
    current_rule_data = get_api_rule_set(entity_name)
    if current_rule_data:
        current_template = load_payload_template(entity_name)
        add_to_history(entity_name, current_rule_data, current_template)
    
    # Restore the selected version
    save_api_rule_set(
        entity_name,
        version_to_restore.get('api_type', 'blueprint'),
        version_to_restore.get('rules', []),
        version_to_restore.get('payload_template'),
        version_to_restore.get('scalable_entities', []),
        version_to_restore.get('task_execution', 'parallel')
    )
    
    return True

# ============================================================================
# ID DETECTION AND HANDLING
# ============================================================================

ID_FIELD_PATTERNS = [
    r'^uuid$', r'^id$', r'^_id$',
    r'.*_uuid$', r'.*_id$', r'.*Id$', r'.*Uuid$',
    r'^guid$', r'.*_guid$', r'.*Guid$',
    r'^key$', r'.*_key$', r'.*Key$',
    r'^ref$', r'.*_ref$', r'.*Ref$',
    r'^identifier$', r'.*_identifier$',
]

def is_id_field(field_name: str) -> bool:
    """Check if a field name matches ID/UUID patterns."""
    for pattern in ID_FIELD_PATTERNS:
        if re.match(pattern, field_name, re.IGNORECASE):
            # Debug: Log when problematic fields are identified as ID fields
            if field_name in ['type', 'mac_address']:
                logger.info(f"DEBUG: Field '{field_name}' matched ID pattern '{pattern}'")
            return True
    return False

def is_uuid_like(value: Any) -> bool:
    """Check if a value looks like a UUID."""
    if not isinstance(value, str):
        return False
    uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    return bool(re.match(uuid_pattern, value))

def generate_new_id(original_value: Any, index: int) -> Any:
    """Generate a new unique ID based on the original value type."""
    # Debug: Log when called with empty strings
    if original_value == "":
        logger.info(f"DEBUG: generate_new_id called with empty string, index={index}")
    
    if is_uuid_like(original_value):
        return str(uuid.uuid4())
    elif isinstance(original_value, int):
        return original_value + index
    elif isinstance(original_value, str):
        if original_value:
            match = re.match(r'^(.+?)(\d+)$', original_value)
            if match:
                base, num = match.groups()
                result = f"{base}{int(num) + index}"
                logger.info(f"DEBUG: generate_new_id: '{original_value}' -> '{result}' (string with number)")
                return result
            result = f"{original_value}_{index + 1}"
            logger.info(f"DEBUG: generate_new_id: '{original_value}' -> '{result}' (non-empty string)")
            return result
        # Keep empty strings as empty strings - don't scale them
        logger.info(f"DEBUG: generate_new_id: keeping empty string as empty string")
        return original_value
    return original_value

def collect_all_id_values(data: Any, path: str = "", id_values: Dict[str, Set[Any]] = None) -> Dict[str, Set[Any]]:
    """Collect all ID field values from the payload."""
    if id_values is None:
        id_values = {}
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            if is_id_field(key) and isinstance(value, (str, int)):
                if current_path not in id_values:
                    id_values[current_path] = set()
                id_values[current_path].add(value)
            elif isinstance(value, dict):
                collect_all_id_values(value, current_path, id_values)
            elif isinstance(value, list):
                for item in enumerate(value):
                    if isinstance(item[1], dict):
                        collect_all_id_values(item[1], current_path, id_values)
    
    elif isinstance(data, list):
        for item in enumerate(data):
            if isinstance(item[1], dict):
                collect_all_id_values(item[1], path, id_values)
    
    return id_values

def find_references(data: Any, id_values: Dict[str, Set[Any]], path: str = "", references: Dict[str, List[str]] = None) -> Dict[str, List[str]]:
    """Find where ID values are referenced in other parts of the payload."""
    if references is None:
        references = {}
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, (str, int)):
                for id_path, values in id_values.items():
                    if value in values and current_path != id_path:
                        if id_path not in references:
                            references[id_path] = []
                        if current_path not in references[id_path]:
                            references[id_path].append(current_path)
            elif isinstance(value, dict):
                find_references(value, id_values, current_path, references)
            elif isinstance(value, list):
                for _, item in enumerate(value):
                    if isinstance(item, dict):
                        find_references(item, id_values, current_path, references)
                    elif isinstance(item, (str, int)):
                        for id_path, values in id_values.items():
                            if item in values:
                                if id_path not in references:
                                    references[id_path] = []
                                if current_path not in references[id_path]:
                                    references[id_path].append(current_path)
    
    elif isinstance(data, list):
        for item in enumerate(data):
            if isinstance(item[1], dict):
                find_references(item[1], id_values, path, references)
    
    return references

# ============================================================================
# ENTITY DETECTION
# ============================================================================

# Entities that should NOT be scaled (they have semantic meaning)
# These apply to BLUEPRINT payloads
# NOTE: action_list, variable_list, and task_definition_list are now conditionally scalable
# They can be scaled if explicitly specified in entity_counts with full paths
NON_SCALABLE_ENTITIES_BLUEPRINT = {
    'edges',  # Task edges should not be scaled
    'child_tasks_local_reference_list',  # Child task references should not be scaled (auto-updated)
    'environment_reference_list',  # Environment references should not be scaled
    'patch_list',  # Patches should not be scaled
    'restore_config_list',  # Restore configs should not be scaled
    'snapshot_config_list',  # Snapshot configs should not be scaled
    'port_list',  # Ports should not be scaled
    'depends_on_list',  # Dependencies should not be scaled
    'published_service_definition_list',  # Published services should not be scaled
}

# For RUNBOOK payloads - tasks CAN be scaled (we handle DAG references)
NON_SCALABLE_ENTITIES_RUNBOOK = {
    'variable_list',  # Variables should not be duplicated
    'edges',  # Task edges should not be scaled
    'child_tasks_local_reference_list',  # Auto-updated when tasks scale
}

# Default (used when api_type not specified)
NON_SCALABLE_ENTITIES = NON_SCALABLE_ENTITIES_BLUEPRINT

# Entities that are auto-linked to service count (scales automatically with services)
AUTO_LINKED_ENTITIES = {
    'substrate_definition_list',  # Same count as services
    'package_definition_list',  # Same count as services
    'deployment_create_list',  # Same count as services
}

# Entities that have fixed default count (not auto-linked, but not main scalable either)
FIXED_COUNT_ENTITIES = {
    'credential_definition_list': 1,  # Usually keep at 1 (shared credential)
    'app_profile_list': 1,  # Usually 1 profile
}

# Main scalable entity for Blueprint
BLUEPRINT_MAIN_ENTITY = 'spec.resources.service_definition_list'

def get_non_scalable_entities(api_type: str = 'blueprint') -> set:
    """Get the set of non-scalable entities based on API type."""
    if api_type == 'runbook':
        return NON_SCALABLE_ENTITIES_RUNBOOK
    return NON_SCALABLE_ENTITIES_BLUEPRINT


def find_entities_in_payload(data: Any, path: str = "", entities: Dict[str, Any] = None, api_type: str = 'blueprint') -> Dict[str, Any]:
    """Recursively find all entities (arrays) in the payload that could be scaled."""
    if entities is None:
        entities = {}
    
    non_scalable = get_non_scalable_entities(api_type)
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            # Skip non-scalable entities based on API type
            # BUT: Allow nested paths to be scalable if explicitly specified in entity_counts
            # This allows paths like "service_definition_list.action_list" even if "action_list" is in non_scalable
            if key in non_scalable:
                # Still recurse into the content but don't add as scalable entity
                # This allows nested entities to be found and scaled
                if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                    find_entities_in_payload(value[0], current_path, entities, api_type)
                continue
            
            if isinstance(value, list):
                if len(value) > 0:
                    sample = value[0] if isinstance(value[0], dict) else value[0]
                    
                    id_fields = []
                    if isinstance(value[0], dict):
                        for k, v in value[0].items():
                            if is_id_field(k):
                                id_fields.append({
                                    'field': k,
                                    'path': f"{current_path}.{k}",
                                    'sample_value': v
                                })
                    
                    # Check if this is an auto-linked entity (hidden from main UI)
                    is_auto_linked = key in AUTO_LINKED_ENTITIES
                    
                    entities[current_path] = {
                        'type': 'array',
                        'current_count': len(value),
                        'sample': sample,
                        'path': current_path,
                        'id_fields': id_fields,
                        'auto_linked': is_auto_linked
                    }
                    # Recurse into first array element
                    if isinstance(value[0], dict):
                        find_entities_in_payload(value[0], current_path, entities, api_type)
                else:
                    is_auto_linked = key in AUTO_LINKED_ENTITIES
                    entities[current_path] = {
                        'type': 'array',
                        'current_count': 0,
                        'sample': None,
                        'path': current_path,
                        'id_fields': [],
                        'auto_linked': is_auto_linked
                    }
            else:
                find_entities_in_payload(value, current_path, entities, api_type)
    
    elif isinstance(data, list):
        if len(data) > 0:
            sample = data[0] if isinstance(data[0], dict) else data[0]
            
            id_fields = []
            if isinstance(data[0], dict):
                for k, v in data[0].items():
                    if is_id_field(k):
                        id_fields.append({
                            'field': k,
                            'path': f"{path or 'root'}.{k}",
                            'sample_value': v
                        })
            
            # Get the last part of the path to check if auto-linked
            path_parts = (path or 'root').split('.')
            last_part = path_parts[-1] if path_parts else 'root'
            is_auto_linked = last_part in AUTO_LINKED_ENTITIES
            
            entities[path or 'root'] = {
                'type': 'array',
                'current_count': len(data),
                'sample': sample,
                'path': path or 'root',
                'id_fields': id_fields,
                'auto_linked': is_auto_linked
            }
            if isinstance(data[0], dict):
                find_entities_in_payload(data[0], path or 'root', entities, api_type)
    
    return entities

# ============================================================================
# SCALING LOGIC
# ============================================================================

def regenerate_all_ids_in_object(obj: Any, index: int, id_mapping: Dict, base_path: str) -> Any:
    """
    Recursively regenerate all ID fields in an object (including nested objects).
    This handles cases like options.install_runbook.uuid
    """
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            current_path = f"{base_path}.{key}" if base_path else key
            
            if is_id_field(key) and isinstance(value, (str, int)):
                # Generate new ID for this field
                new_id = generate_new_id(value, index)
                
                if current_path not in id_mapping:
                    id_mapping[current_path] = {}
                if value not in id_mapping[current_path]:
                    id_mapping[current_path][value] = []
                id_mapping[current_path][value].append(new_id)
                
                result[key] = new_id
            elif isinstance(value, dict):
                # Recursively process nested objects
                result[key] = regenerate_all_ids_in_object(value, index, id_mapping, current_path)
            elif isinstance(value, list):
                # Process lists (but don't regenerate IDs in nested arrays - those are handled by scaling)
                result[key] = value  # Keep as-is for now, will be processed during recursive scaling
            else:
                result[key] = value
        return result
    elif isinstance(obj, list):
        return [regenerate_all_ids_in_object(item, index, id_mapping, base_path) for item in obj]
    else:
        return obj


def scale_payload_with_ids(data: Any, entity_counts: Dict[str, int], id_mapping: Dict[str, Dict[Any, List[Any]]], path: str = "", current_indices: Dict[str, int] = None) -> Any:
    """Recursively scale the payload based on entity counts, generating new IDs."""
    if current_indices is None:
        current_indices = {}
    
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            if current_path in entity_counts:
                count = entity_counts[current_path]
                if isinstance(value, list) and len(value) > 0:
                    sample = value[0]
                    scaled_samples = []
                    
                    for i in range(count):
                        scaled_sample = copy.deepcopy(sample)
                        
                        # Regenerate ALL ID fields in this sample, including nested ones
                        if isinstance(scaled_sample, dict):
                            scaled_sample = regenerate_all_ids_in_object(scaled_sample, i, id_mapping, current_path)
                        
                        current_indices[current_path] = i
                        scaled_sample = scale_payload_with_ids(scaled_sample, entity_counts, id_mapping, current_path, current_indices)
                        scaled_samples.append(scaled_sample)
                    
                    result[key] = scaled_samples
                else:
                    result[key] = value
            else:
                result[key] = scale_payload_with_ids(value, entity_counts, id_mapping, current_path, current_indices)
        return result
    
    elif isinstance(data, list):
        root_path = path or 'root'
        if root_path in entity_counts:
            count = entity_counts[root_path]
            if len(data) > 0:
                sample = data[0]
                scaled_samples = []
                
                for i in range(count):
                    scaled_sample = copy.deepcopy(sample)
                    
                    # Regenerate ALL ID fields in this sample, including nested ones
                    if isinstance(scaled_sample, dict):
                        scaled_sample = regenerate_all_ids_in_object(scaled_sample, i, id_mapping, root_path)
                    
                    current_indices[root_path] = i
                    scaled_sample = scale_payload_with_ids(scaled_sample, entity_counts, id_mapping, root_path, current_indices)
                    scaled_samples.append(scaled_sample)
                
                return scaled_samples
        return [scale_payload_with_ids(item, entity_counts, id_mapping, path, current_indices) for item in data]
    
    return data

def update_references(data: Any, id_mapping: Dict[str, Dict[Any, List[Any]]], reference_map: Dict[str, List[str]], path: str = "", array_indices: Dict[str, int] = None) -> Any:
    """Update all references in the payload to use the new generated IDs."""
    if array_indices is None:
        array_indices = {}
    
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, (str, int)):
                updated = False
                for source_id_path in reference_map:
                    if source_id_path in id_mapping:
                        for original_val, new_vals in id_mapping[source_id_path].items():
                            if value == original_val and new_vals:
                                idx = sum(array_indices.values()) % len(new_vals) if array_indices else 0
                                result[key] = new_vals[min(idx, len(new_vals) - 1)]
                                updated = True
                                break
                    if updated:
                        break
                
                if not updated:
                    for source_id_path, val_map in id_mapping.items():
                        if value in val_map and val_map[value]:
                            idx = sum(array_indices.values()) % len(val_map[value]) if array_indices else 0
                            result[key] = val_map[value][min(idx, len(val_map[value]) - 1)]
                            updated = True
                            break
                    
                    if not updated:
                        result[key] = value
            elif isinstance(value, dict):
                result[key] = update_references(value, id_mapping, reference_map, current_path, array_indices)
            elif isinstance(value, list):
                updated_list = []
                for i, item in enumerate(value):
                    new_indices = array_indices.copy()
                    new_indices[current_path] = i
                    if isinstance(item, dict):
                        updated_list.append(update_references(item, id_mapping, reference_map, current_path, new_indices))
                    elif isinstance(item, (str, int)):
                        updated_item = item
                        for source_id_path, val_map in id_mapping.items():
                            if item in val_map and val_map[item]:
                                idx = i % len(val_map[item])
                                updated_item = val_map[item][idx]
                                break
                        updated_list.append(updated_item)
                    else:
                        updated_list.append(item)
                result[key] = updated_list
            else:
                result[key] = value
        return result
    
    elif isinstance(data, list):
        updated_list = []
        for i, item in enumerate(data):
            new_indices = array_indices.copy()
            new_indices[path or 'root'] = i
            if isinstance(item, dict):
                updated_list.append(update_references(item, id_mapping, reference_map, path, new_indices))
            else:
                updated_list.append(item)
        return updated_list
    
    return data

def scale_payload(data: Any, entity_counts: Dict[str, int], path: str = "") -> Any:
    """Scale the payload with proper ID generation and reference updates."""
    id_values = collect_all_id_values(data)
    reference_map = find_references(data, id_values)
    id_mapping = {}
    scaled = scale_payload_with_ids(data, entity_counts, id_mapping, path)
    
    if id_mapping and reference_map:
        scaled = update_references(scaled, id_mapping, reference_map)
    
    return scaled

# ============================================================================
# RULE APPLICATION
# ============================================================================

def apply_single_source_rule(data: Any, rule: Dict[str, Any]) -> Any:
    """Apply a 'use_single' rule - use only one item from a source entity everywhere."""
    source_path = rule.get('source_entity', '')
    
    if not source_path:
        return data
    
    parts = source_path.split('.')
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return data
    
    if not isinstance(current, list) or len(current) == 0:
        return data
    
    first_item = current[0]
    first_id = None
    
    if isinstance(first_item, dict):
        for key in ['uuid', 'id', '_id']:
            if key in first_item:
                first_id = first_item[key]
                break
    
    if first_id is None:
        return data
    
    all_ids = set()
    for item in current:
        if isinstance(item, dict):
            for key in ['uuid', 'id', '_id']:
                if key in item:
                    all_ids.add(item[key])
                    break
    
    def replace_ids(obj):
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if isinstance(v, (str, int)) and v in all_ids:
                    result[k] = first_id
                else:
                    result[k] = replace_ids(v)
            return result
        elif isinstance(obj, list):
            return [replace_ids(item) for item in obj]
        else:
            return obj
    
    return replace_ids(data)


def apply_reference_mapping_rule(data: Any, rule: Dict[str, Any]) -> Any:
    """Apply a reference mapping rule - map references from one entity to another."""
    source_path = rule.get('source_path', '')
    target_path = rule.get('target_path', '')
    mapping_type = rule.get('mapping_type', 'one_to_one')
    
    if not source_path or not target_path:
        return data
    
    source_ids = collect_ids_from_path(data, source_path)
    
    if not source_ids:
        return data
    
    if mapping_type == 'first_only':
        first_id = source_ids[0] if source_ids else None
        if first_id:
            return replace_at_path(data, target_path, lambda idx, old_val: first_id)
    elif mapping_type == 'round_robin':
        return replace_at_path(data, target_path, lambda idx, old_val: source_ids[idx % len(source_ids)])
    else:
        return replace_at_path(data, target_path, lambda idx, old_val: source_ids[idx] if idx < len(source_ids) else old_val)
    
    return data


def collect_ids_from_path(data: Any, path: str) -> List[Any]:
    """
    Collect all ID values from a given path pattern.
    Handles nested arrays like spec.resources.package_definition_list.uuid
    """
    parts = path.split('.')
    ids = []
    
    def traverse(obj, remaining_parts, collected):
        if not remaining_parts:
            if isinstance(obj, (str, int)):
                collected.append(obj)
            elif isinstance(obj, list):
                # If we end up at a list, collect from each item
                for item in obj:
                    if isinstance(item, (str, int)):
                        collected.append(item)
            return
        
        part = remaining_parts[0]
        rest = remaining_parts[1:]
        
        if isinstance(obj, dict):
            if part in obj:
                traverse(obj[part], rest, collected)
            # Also check for partial path matches in nested structures
        elif isinstance(obj, list):
            # Traverse into each list item
            for item in obj:
                if isinstance(item, dict):
                    if part in item:
                        traverse(item[part], rest, collected)
                    else:
                        # Continue searching with same parts
                        traverse(item, remaining_parts, collected)
    
    traverse(data, parts, ids)
    return ids


def replace_at_path(data: Any, path: str, replacer) -> Any:
    """
    Replace values at a given path pattern.
    Handles deeply nested paths with arrays like:
    spec.resources.app_profile_list.deployment_create_list.package_local_reference_list.uuid
    """
    parts = path.split('.')
    counter = [0]
    
    def traverse(obj, remaining_parts, depth=0):
        if not remaining_parts:
            return obj
        
        part = remaining_parts[0]
        rest = remaining_parts[1:]
        
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k == part:
                    if not rest:
                        # This is the target field - replace it
                        if isinstance(v, list):
                            # If the target is a list of values, replace each
                            new_list = []
                            for item in v:
                                if isinstance(item, (str, int)):
                                    new_list.append(replacer(counter[0], item))
                                    counter[0] += 1
                                else:
                                    new_list.append(item)
                            result[k] = new_list
                        else:
                            new_val = replacer(counter[0], v)
                            counter[0] += 1
                            result[k] = new_val
                    else:
                        result[k] = traverse(v, rest, depth + 1)
                else:
                    # Continue searching in other keys
                    result[k] = traverse(v, remaining_parts, depth)
            return result
        elif isinstance(obj, list):
            result = []
            for item in obj:
                if isinstance(item, dict):
                    # Check if this dict has the part we're looking for
                    if part in item:
                        result.append(traverse(item, remaining_parts, depth))
                    else:
                        # Keep traversing
                        result.append(traverse(item, remaining_parts, depth))
                else:
                    result.append(item)
            return result
        else:
            return obj
    
    return traverse(data, parts)


def apply_filter_rule(data: Any, rule: Dict[str, Any]) -> Any:
    """Apply a filter rule - keep only items matching allowed values."""
    target_path = rule.get('target_path', '')
    filter_field = rule.get('filter_field', 'name')
    allowed_values = rule.get('allowed_values', [])
    
    if not target_path or not allowed_values:
        return data
    
    parts = target_path.split('.')
    
    def filter_at_path(obj, remaining_parts):
        if not remaining_parts:
            if isinstance(obj, list):
                return [item for item in obj if isinstance(item, dict) and item.get(filter_field) in allowed_values]
            return obj
        
        part = remaining_parts[0]
        rest = remaining_parts[1:]
        
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k == part:
                    result[k] = filter_at_path(v, rest)
                else:
                    result[k] = filter_at_path(v, remaining_parts)
            return result
        elif isinstance(obj, list):
            return [filter_at_path(item, remaining_parts) for item in obj]
        else:
            return obj
    
    return filter_at_path(data, parts)


def apply_clone_rule(data: Any, rule: Dict[str, Any]) -> Any:
    """Apply a clone rule - find an item matching a condition and clone it."""
    target_path = rule.get('target_path', '')
    source_field = rule.get('source_field', 'name')
    source_value = rule.get('source_value', '')
    clone_values = rule.get('clone_values', [])
    
    if not target_path or not source_value:
        return data
    
    parts = target_path.split('.')
    
    def clone_at_path(obj, remaining_parts):
        if not remaining_parts:
            if isinstance(obj, list):
                source_item = None
                for item in obj:
                    if isinstance(item, dict) and item.get(source_field) == source_value:
                        source_item = item
                        break
                
                if source_item:
                    new_items = list(obj)
                    for new_value in clone_values:
                        cloned = copy.deepcopy(source_item)
                        cloned[source_field] = new_value
                        if 'uuid' in cloned:
                            cloned['uuid'] = str(uuid.uuid4())
                        new_items.append(cloned)
                    return new_items
            return obj
        
        part = remaining_parts[0]
        rest = remaining_parts[1:]
        
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k == part:
                    result[k] = clone_at_path(v, rest)
                else:
                    result[k] = clone_at_path(v, remaining_parts)
            return result
        elif isinstance(obj, list):
            return [clone_at_path(item, remaining_parts) for item in obj]
        else:
            return obj
    
    return clone_at_path(data, parts)


def apply_set_value_rule(data: Any, rule: Dict[str, Any]) -> Any:
    """Apply a set value rule - set a specific field to a specific value."""
    target_path = rule.get('target_path', '')
    new_value = rule.get('new_value', '')
    
    if not target_path:
        return data
    
    parts = target_path.split('.')
    
    def set_at_path(obj, remaining_parts):
        if not remaining_parts:
            return new_value
        
        part = remaining_parts[0]
        rest = remaining_parts[1:]
        
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k == part:
                    if not rest:
                        result[k] = new_value
                    else:
                        result[k] = set_at_path(v, rest)
                else:
                    result[k] = set_at_path(v, remaining_parts)
            return result
        elif isinstance(obj, list):
            return [set_at_path(item, remaining_parts) for item in obj]
        else:
            return obj
    
    return set_at_path(data, parts)


def apply_keep_first_rule(data: Any, rule: Dict[str, Any]) -> Any:
    """Apply a keep first N rule - keep only the first N items in a list."""
    target_path = rule.get('target_path', '')
    keep_count = rule.get('keep_count', 1)
    
    if not target_path:
        return data
    
    parts = target_path.split('.')
    
    def keep_first_at_path(obj, remaining_parts):
        if not remaining_parts:
            if isinstance(obj, list):
                return obj[:keep_count]
            return obj
        
        part = remaining_parts[0]
        rest = remaining_parts[1:]
        
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k == part:
                    result[k] = keep_first_at_path(v, rest)
                else:
                    result[k] = keep_first_at_path(v, remaining_parts)
            return result
        elif isinstance(obj, list):
            return [keep_first_at_path(item, remaining_parts) for item in obj]
        else:
            return obj
    
    return keep_first_at_path(data, parts)


def apply_remove_field_rule(data: Any, rule: Dict[str, Any]) -> Any:
    """Apply a remove field rule - remove a specific field from objects at a path."""
    target_path = rule.get('target_path', '')
    field_to_remove = rule.get('field_to_remove', '')
    
    if not target_path or not field_to_remove:
        return data
    
    parts = target_path.split('.')
    
    def remove_at_path(obj, remaining_parts):
        if not remaining_parts:
            if isinstance(obj, dict):
                return {k: v for k, v in obj.items() if k != field_to_remove}
            elif isinstance(obj, list):
                return [{k: v for k, v in item.items() if k != field_to_remove} if isinstance(item, dict) else item for item in obj]
            return obj
        
        part = remaining_parts[0]
        rest = remaining_parts[1:]
        
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k == part:
                    result[k] = remove_at_path(v, rest)
                else:
                    result[k] = remove_at_path(v, remaining_parts)
            return result
        elif isinstance(obj, list):
            return [remove_at_path(item, remaining_parts) for item in obj]
        else:
            return obj
    
    return remove_at_path(data, parts)


def apply_name_suffix_to_entities(data: Any, entity_counts: Dict[str, int]) -> Any:
    """
    Add suffix to 'name' field of scaled entities to make them unique.
    E.g., if scaling service_definition_list to 3, names become: MyService_1, MyService_2, MyService_3
    
    EXCEPTION: Action names (action_create, action_delete, etc.) are NOT modified.
    """
    # Skip these entity paths - their names have semantic meaning
    skip_name_suffix_paths = {
        'action_list',  # Action names should not be changed
    }
    
    for entity_path, count in entity_counts.items():
        if count <= 1:
            continue
        
        # Skip entities whose names shouldn't be changed
        path_parts = entity_path.split('.')
        if any(part in skip_name_suffix_paths for part in path_parts):
            continue
        
        parts = path_parts
        
        def add_suffix_at_path(obj, remaining_parts, indices=None):
            if indices is None:
                indices = {}
            
            if not remaining_parts:
                if isinstance(obj, list):
                    result = []
                    for i, item in enumerate(obj):
                        if isinstance(item, dict) and 'name' in item:
                            item = copy.deepcopy(item)
                            original_name = item['name']
                            # Remove any existing suffix like _1, _2 etc
                            base_name = re.sub(r'_\d+$', '', str(original_name))
                            item['name'] = f"{base_name}_{i + 1}"
                        result.append(item)
                    return result
                return obj
            
            part = remaining_parts[0]
            rest = remaining_parts[1:]
            
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    if k == part:
                        result[k] = add_suffix_at_path(v, rest, indices)
                    else:
                        result[k] = add_suffix_at_path(v, remaining_parts, indices)
                return result
            elif isinstance(obj, list):
                return [add_suffix_at_path(item, remaining_parts, indices) for item in obj]
            else:
                return obj
        
        data = add_suffix_at_path(data, parts)
    
    return data


def update_spec_name(data: Any) -> Any:
    """
    Update spec.name to make it unique by adding a timestamp/random suffix.
    This ensures each generated payload has a unique name.
    """
    import time
    if isinstance(data, dict) and 'spec' in data:
        spec = data['spec']
        if isinstance(spec, dict) and 'name' in spec:
            original_name = spec['name']
            # Remove any existing suffix like _scaled_xxxx or _scaled_timestamp_xxxx
            base_name = re.sub(r'_scaled_[a-z0-9_]+$', '', str(original_name))
            # Add a unique suffix with timestamp and random string for guaranteed uniqueness
            timestamp = int(time.time() * 1000) % 100000000  # Last 8 digits of millisecond timestamp
            random_suffix = str(uuid.uuid4())[:4]
            data['spec']['name'] = f"{base_name}_scaled_{timestamp}_{random_suffix}"
    return data


def update_metadata_uuid(data: Any) -> Any:
    """
    Always generate a new UUID for metadata.uuid to ensure payload uniqueness.
    This is critical for creating new resources rather than updating existing ones.
    """
    if isinstance(data, dict) and 'metadata' in data:
        metadata = data['metadata']
        if isinstance(metadata, dict):
            # Always generate new UUID for the main payload
            metadata['uuid'] = str(uuid.uuid4())
    return data


def regenerate_all_entity_uuids(data: Any) -> Any:
    """
    Regenerate ALL UUIDs in the payload to ensure complete uniqueness.
    This is the final step to guarantee no UUID conflicts with existing entities.
    
    This function:
    1. Collects all UUIDs from main entities and builds a mapping
    2. Regenerates ALL UUIDs in the entire payload (not just mapped ones)
    3. Updates all references to use the new UUIDs
    """
    if not isinstance(data, dict) or 'spec' not in data:
        return data
    
    resources = data.get('spec', {}).get('resources', {})
    if not resources:
        return data
    
    # Build a mapping of old UUID -> new UUID for main entities
    # This ensures references between entities are maintained
    uuid_mapping = {}
    
    # Helper to generate and track new UUID
    def get_new_uuid(old_uuid: str) -> str:
        if old_uuid not in uuid_mapping:
            uuid_mapping[old_uuid] = str(uuid.uuid4())
        return uuid_mapping[old_uuid]
    
    # Phase 1: Collect and regenerate UUIDs for all main entities
    entity_lists = [
        'substrate_definition_list',
        'package_definition_list', 
        'service_definition_list',
        'credential_definition_list',
        'app_profile_list'
    ]
    
    for entity_list_name in entity_lists:
        for entity in resources.get(entity_list_name, []):
            if isinstance(entity, dict) and 'uuid' in entity:
                old_uuid = entity['uuid']
                entity['uuid'] = get_new_uuid(old_uuid)
            
            # Handle nested deployments in app_profile_list
            if entity_list_name == 'app_profile_list':
                for deployment in entity.get('deployment_create_list', []):
                    if isinstance(deployment, dict) and 'uuid' in deployment:
                        old_uuid = deployment['uuid']
                        deployment['uuid'] = get_new_uuid(old_uuid)
    
    # Phase 2: Regenerate ALL UUIDs in the entire payload
    # This catches nested UUIDs in runbooks, actions, tasks, etc.
    def regenerate_all_uuids(obj: Any) -> Any:
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if key == 'uuid' and isinstance(value, str):
                    # Check if this UUID is in our mapping (main entity reference)
                    if value in uuid_mapping:
                        result[key] = uuid_mapping[value]
                    elif is_uuid_like(value):
                        # Generate new UUID for any UUID-like value not in mapping
                        # This handles nested runbooks, actions, tasks, etc.
                        result[key] = str(uuid.uuid4())
                    else:
                        result[key] = value
                elif isinstance(value, (dict, list)):
                    result[key] = regenerate_all_uuids(value)
                else:
                    result[key] = value
            return result
        elif isinstance(obj, list):
            return [regenerate_all_uuids(item) for item in obj]
        return obj
    
    # Apply UUID regeneration to entire payload
    data = regenerate_all_uuids(data)
    
    return data


def regenerate_task_uuids(runbook: Dict) -> None:
    """
    Regenerate UUIDs for all tasks in a runbook's task_definition_list.
    Also updates main_task_local_reference to match the first task's new UUID.
    """
    if not isinstance(runbook, dict):
        return
    
    tasks = runbook.get('task_definition_list', [])
    for task in tasks:
        if isinstance(task, dict):
            # Generate new UUID for the task
            task['uuid'] = str(uuid.uuid4())
    
    # Fix main_task_local_reference to match first task's UUID
    if tasks and len(tasks) > 0:
        first_task_uuid = tasks[0].get('uuid')
        if first_task_uuid and 'main_task_local_reference' in runbook:
            runbook['main_task_local_reference']['uuid'] = first_task_uuid


def fix_main_task_reference_mapping(runbook: Dict) -> None:
    """
    Fix main_task_local_reference.uuid to match task_definition_list[0].uuid
    WITHOUT regenerating any UUIDs. This preserves existing UUIDs and only fixes the mapping.
    """
    if not isinstance(runbook, dict):
        return
    
    tasks = runbook.get('task_definition_list', [])
    if tasks and len(tasks) > 0:
        first_task = tasks[0]
        if isinstance(first_task, dict) and 'uuid' in first_task:
            first_task_uuid = first_task['uuid']
            if 'main_task_local_reference' in runbook:
                if isinstance(runbook['main_task_local_reference'], dict):
                    runbook['main_task_local_reference']['uuid'] = first_task_uuid


def fix_all_runbooks_in_object(obj: Any) -> None:
    """
    Recursively find all runbooks in an object and:
    Fix main_task_local_reference.uuid = task_definition_list[0].uuid
    WITHOUT regenerating UUIDs (preserves existing UUIDs)
    """
    if isinstance(obj, dict):
        # Check if this dict IS a runbook (has task_definition_list and main_task_local_reference)
        if 'task_definition_list' in obj and 'main_task_local_reference' in obj:
            # Only fix the mapping, don't regenerate UUIDs
            fix_main_task_reference_mapping(obj)
        
        # Recurse into all values
        for value in obj.values():
            fix_all_runbooks_in_object(value)
    
    elif isinstance(obj, list):
        for item in obj:
            fix_all_runbooks_in_object(item)


def apply_runbook_rules_to_runbook(runbook: Dict) -> None:
    """
    Apply runbook entity rules to a single runbook.
    Updates DAG child_tasks_local_reference_list and edges based on current task structure.
    This ensures DAG references are always correct after task scaling.
    
    Handles two scenarios:
    1. 1 DAG + multiple EXEC tasks: DAG references EXEC tasks
    2. Multiple DAG tasks: First DAG references other DAGs
    
    Args:
        runbook: The runbook dictionary to update
    """
    if not isinstance(runbook, dict):
        return
    
    tasks = runbook.get('task_definition_list', [])
    if not tasks:
        return
    
    # Find DAG tasks and EXEC tasks
    dag_tasks = []
    exec_tasks = []
    for task in tasks:
        if task.get('type') == 'DAG':
            dag_tasks.append(task)
        else:
            exec_tasks.append(task)
    
    # Scenario 1: 1 DAG + multiple EXEC tasks
    if len(dag_tasks) == 1 and len(exec_tasks) > 0:
        dag_task = dag_tasks[0]
        # Update DAG's child_tasks_local_reference_list with all EXEC task UUIDs
        dag_task['child_tasks_local_reference_list'] = [
            {'kind': 'app_task', 'uuid': task['uuid']}
            for task in exec_tasks
        ]
        
        # Update edges in DAG - preserve original edges structure if exists
        if 'attrs' not in dag_task:
            dag_task['attrs'] = {}
        
        original_edges = dag_task.get('attrs', {}).get('edges', [])
        if original_edges and len(original_edges) > 0 and len(exec_tasks) > 1:
            # Series mode: create sequential edges (Task1 -> Task2 -> Task3...)
            edges = []
            for i in range(len(exec_tasks) - 1):
                edge = {
                    'from_task_reference': {
                        'kind': 'app_task',
                        'uuid': exec_tasks[i]['uuid']
                    },
                    'to_task_reference': {
                        'kind': 'app_task',
                        'uuid': exec_tasks[i + 1]['uuid']
                    },
                    'uuid': str(uuid.uuid4())
                }
                edges.append(edge)
            dag_task['attrs']['edges'] = edges
        else:
            # Parallel mode: no edges (all tasks run simultaneously)
            dag_task['attrs']['edges'] = []
        
        # Update main_task_local_reference to point to DAG
        if 'main_task_local_reference' in runbook:
            runbook['main_task_local_reference']['uuid'] = dag_task['uuid']
    
    # Scenario 2: Multiple DAG tasks (all tasks are DAGs)
    elif len(dag_tasks) > 1:
        # First DAG is the main task, others are child DAGs
        main_dag = dag_tasks[0]
        child_dags = dag_tasks[1:]
        
        # Update main DAG's child_tasks_local_reference_list with other DAG UUIDs
        main_dag['child_tasks_local_reference_list'] = [
            {'kind': 'app_task', 'uuid': dag['uuid']}
            for dag in child_dags
        ]
        
        # Update edges in main DAG - create sequential edges between DAGs
        if 'attrs' not in main_dag:
            main_dag['attrs'] = {}
        
        original_edges = main_dag.get('attrs', {}).get('edges', [])
        if original_edges and len(original_edges) > 0 and len(child_dags) > 1:
            # Series mode: create sequential edges (DAG1 -> DAG2 -> DAG3...)
            edges = []
            for i in range(len(child_dags) - 1):
                edge = {
                    'from_task_reference': {
                        'kind': 'app_task',
                        'uuid': child_dags[i]['uuid']
                    },
                    'to_task_reference': {
                        'kind': 'app_task',
                        'uuid': child_dags[i + 1]['uuid']
                    },
                    'uuid': str(uuid.uuid4())
                }
                edges.append(edge)
            main_dag['attrs']['edges'] = edges
        elif len(child_dags) > 1:
            # If no original edges but multiple child DAGs, create sequential edges
            edges = []
            for i in range(len(child_dags) - 1):
                edge = {
                    'from_task_reference': {
                        'kind': 'app_task',
                        'uuid': child_dags[i]['uuid']
                    },
                    'to_task_reference': {
                        'kind': 'app_task',
                        'uuid': child_dags[i + 1]['uuid']
                    },
                    'uuid': str(uuid.uuid4())
                }
                edges.append(edge)
            main_dag['attrs']['edges'] = edges
        else:
            # Single child DAG or parallel mode: no edges
            main_dag['attrs']['edges'] = []
        
        # Update main_task_local_reference to point to first DAG
        if 'main_task_local_reference' in runbook:
            runbook['main_task_local_reference']['uuid'] = main_dag['uuid']
    
    # Scenario 3: Single DAG with no EXEC tasks (edge case)
    elif len(dag_tasks) == 1 and len(exec_tasks) == 0:
        dag_task = dag_tasks[0]
        # No child tasks, so empty list
        dag_task['child_tasks_local_reference_list'] = []
        if 'attrs' not in dag_task:
            dag_task['attrs'] = {}
        dag_task['attrs']['edges'] = []
        
        # Update main_task_local_reference to point to DAG
        if 'main_task_local_reference' in runbook:
            runbook['main_task_local_reference']['uuid'] = dag_task['uuid']


def apply_blueprint_specific_fixes(data: Any, blueprint_type: str = 'multi_vm', entity_counts: Dict[str, int] = None, runbook_rules: Dict[str, Any] = None) -> Any:
    """
    Apply blueprint-specific reference fixes after scaling.
    This handles complex internal references that can't be done with generic rules.
    Also applies runbook entity rules to all runbooks in the blueprint.
    
    Args:
        data: The payload data
        blueprint_type: 'single_vm' or 'multi_vm'
        entity_counts: Dictionary of entity path -> count for nested entity scaling
        runbook_rules: Runbook default rules to apply to blueprint runbooks
    """
    if entity_counts is None:
        entity_counts = {}
    if runbook_rules is None:
        runbook_rules = {}
    if not isinstance(data, dict) or 'spec' not in data:
        return data
    
    resources = data.get('spec', {}).get('resources', {})
    if not resources:
        return data
    
    # For single_vm, apply simplifications
    if blueprint_type == 'single_vm':
        # Clear client_attrs
        resources['client_attrs'] = {}
        # Delete published_service_definition_list
        if 'published_service_definition_list' in resources:
            del resources['published_service_definition_list']
        # Remove patch_list from each app_profile
        for profile in resources.get('app_profile_list', []):
            if 'patch_list' in profile:
                del profile['patch_list']
    
    # Collect all entity UUIDs for cross-reference fixing
    substrate_uuids = [s.get('uuid') for s in resources.get('substrate_definition_list', []) if s.get('uuid')]
    package_uuids = [p.get('uuid') for p in resources.get('package_definition_list', []) if p.get('uuid')]
    service_uuids = [s.get('uuid') for s in resources.get('service_definition_list', []) if s.get('uuid')]
    
    # 1. Fix default_credential_local_reference to match first credential
    creds = resources.get('credential_definition_list', [])
    if creds and len(creds) > 0:
        first_cred_uuid = creds[0].get('uuid')
        if first_cred_uuid:
            # Update default_credential_local_reference
            if 'default_credential_local_reference' in resources:
                resources['default_credential_local_reference']['uuid'] = first_cred_uuid
            
            # Update all substrate readiness_probe and default_credential_local_reference
            for substrate in resources.get('substrate_definition_list', []):
                if 'readiness_probe' in substrate and 'login_credential_local_reference' in substrate['readiness_probe']:
                    substrate['readiness_probe']['login_credential_local_reference']['uuid'] = first_cred_uuid
                if 'default_credential_local_reference' in substrate:
                    substrate['default_credential_local_reference']['uuid'] = first_cred_uuid
    
    # 2. Fix package internal references
    for pkg in resources.get('package_definition_list', []):
        pkg_uuid = pkg.get('uuid')
        if pkg_uuid and 'options' in pkg:
            options = pkg['options']
            
            # Scale install_runbook tasks and variables if specified in entity_counts
            if 'install_runbook' in options:
                install_rb = options['install_runbook']
                # Generate unique UUID for install_runbook
                install_rb['uuid'] = str(uuid.uuid4())
                
                # Scale task_definition_list if specified
                task_path = 'options.install_runbook.task_definition_list'
                if task_path in entity_counts:
                    task_count = entity_counts[task_path]
                    tasks = install_rb.get('task_definition_list', [])
                    
                    # Find DAG tasks and EXEC tasks
                    dag_tasks = []
                    exec_tasks = []
                    for task in tasks:
                        if task.get('type') == 'DAG':
                            dag_tasks.append(task)
                        else:
                            exec_tasks.append(task)
                    
                    # Scenario 1: 1 DAG + EXEC tasks
                    if len(dag_tasks) == 1 and len(exec_tasks) > 0:
                        dag_task = dag_tasks[0]
                        # Scale EXEC tasks (DAG is always 1)
                        desired_exec_count = max(1, task_count - 1)  # task_count includes DAG
                        
                        if desired_exec_count > len(exec_tasks):
                            # Scale up: duplicate first EXEC task
                            first_exec = exec_tasks[0]
                            for i in range(desired_exec_count - len(exec_tasks)):
                                new_task = copy.deepcopy(first_exec)
                                new_task['uuid'] = str(uuid.uuid4())
                                # Update task name with suffix
                                original_name = first_exec.get('name', 'Task')
                                new_task['name'] = f"{original_name}_{len(exec_tasks) + i + 1}"
                                exec_tasks.append(new_task)
                        elif desired_exec_count < len(exec_tasks):
                            # Scale down: keep only desired count
                            exec_tasks = exec_tasks[:desired_exec_count]
                        
                        # Rebuild task list: DAG first, then EXEC tasks
                        install_rb['task_definition_list'] = [dag_task] + exec_tasks
                    
                    # Scenario 2: Multiple DAG tasks (all tasks are DAGs)
                    elif len(dag_tasks) > 1:
                        # Scale DAG tasks (keep first DAG as main, scale others)
                        desired_dag_count = task_count  # All tasks are DAGs
                        
                        if desired_dag_count > len(dag_tasks):
                            # Scale up: duplicate first child DAG
                            if len(dag_tasks) > 1:
                                first_child_dag = dag_tasks[1]
                                for i in range(desired_dag_count - len(dag_tasks)):
                                    new_dag = copy.deepcopy(first_child_dag)
                                    new_dag['uuid'] = str(uuid.uuid4())
                                    original_name = first_child_dag.get('name', 'DAG')
                                    new_dag['name'] = f"{original_name}_{len(dag_tasks) + i}"
                                    dag_tasks.append(new_dag)
                        elif desired_dag_count < len(dag_tasks):
                            # Scale down: keep only desired count
                            dag_tasks = dag_tasks[:desired_dag_count]
                        
                        install_rb['task_definition_list'] = dag_tasks
                    
                    elif tasks and task_count > len(tasks):
                        # No DAG found, just duplicate first task
                        first_task = tasks[0] if tasks else {}
                        for i in range(task_count - len(tasks)):
                            new_task = copy.deepcopy(first_task)
                            new_task['uuid'] = str(uuid.uuid4())
                            tasks.append(new_task)
                    elif task_count < len(tasks):
                        # Reduce tasks
                        install_rb['task_definition_list'] = tasks[:task_count]
                
                # Scale variable_list if specified
                var_path = 'options.install_runbook.variable_list'
                if var_path in entity_counts:
                    var_count = entity_counts[var_path]
                    vars_list = install_rb.get('variable_list', [])
                    if vars_list and var_count > len(vars_list):
                        first_var = vars_list[0] if vars_list else {}
                        for i in range(var_count - len(vars_list)):
                            new_var = copy.deepcopy(first_var)
                            new_var['uuid'] = str(uuid.uuid4())
                            vars_list.append(new_var)
                    elif var_count < len(vars_list):
                        install_rb['variable_list'] = vars_list[:var_count]
                
                # Fix task target_any_local_reference to point to package
                for task in install_rb.get('task_definition_list', []):
                    if 'target_any_local_reference' in task:
                        if task['target_any_local_reference'].get('kind') == 'app_package':
                            task['target_any_local_reference']['uuid'] = pkg_uuid
                
                # Always apply runbook rules to ensure DAG references are correct (even if tasks weren't scaled)
                apply_runbook_rules_to_runbook(install_rb)
            
            # Scale uninstall_runbook tasks and variables if specified
            if 'uninstall_runbook' in options:
                uninstall_rb = options['uninstall_runbook']
                # Generate unique UUID for uninstall_runbook (different from install)
                uninstall_rb['uuid'] = str(uuid.uuid4())
                
                # Scale task_definition_list if specified
                task_path = 'options.uninstall_runbook.task_definition_list'
                if task_path in entity_counts:
                    task_count = entity_counts[task_path]
                    tasks = uninstall_rb.get('task_definition_list', [])
                    
                    # Find DAG tasks and EXEC tasks
                    dag_tasks = []
                    exec_tasks = []
                    for task in tasks:
                        if task.get('type') == 'DAG':
                            dag_tasks.append(task)
                        else:
                            exec_tasks.append(task)
                    
                    # Scenario 1: 1 DAG + EXEC tasks
                    if len(dag_tasks) == 1 and len(exec_tasks) > 0:
                        dag_task = dag_tasks[0]
                        # Scale EXEC tasks (DAG is always 1)
                        desired_exec_count = max(1, task_count - 1)  # task_count includes DAG
                        
                        if desired_exec_count > len(exec_tasks):
                            # Scale up: duplicate first EXEC task
                            first_exec = exec_tasks[0]
                            for i in range(desired_exec_count - len(exec_tasks)):
                                new_task = copy.deepcopy(first_exec)
                                new_task['uuid'] = str(uuid.uuid4())
                                # Update task name with suffix
                                original_name = first_exec.get('name', 'Task')
                                new_task['name'] = f"{original_name}_{len(exec_tasks) + i + 1}"
                                exec_tasks.append(new_task)
                        elif desired_exec_count < len(exec_tasks):
                            # Scale down: keep only desired count
                            exec_tasks = exec_tasks[:desired_exec_count]
                        
                        # Rebuild task list: DAG first, then EXEC tasks
                        uninstall_rb['task_definition_list'] = [dag_task] + exec_tasks
                    
                    # Scenario 2: Multiple DAG tasks (all tasks are DAGs)
                    elif len(dag_tasks) > 1:
                        # Scale DAG tasks (keep first DAG as main, scale others)
                        desired_dag_count = task_count  # All tasks are DAGs
                        
                        if desired_dag_count > len(dag_tasks):
                            # Scale up: duplicate first child DAG
                            if len(dag_tasks) > 1:
                                first_child_dag = dag_tasks[1]
                                for i in range(desired_dag_count - len(dag_tasks)):
                                    new_dag = copy.deepcopy(first_child_dag)
                                    new_dag['uuid'] = str(uuid.uuid4())
                                    original_name = first_child_dag.get('name', 'DAG')
                                    new_dag['name'] = f"{original_name}_{len(dag_tasks) + i}"
                                    dag_tasks.append(new_dag)
                        elif desired_dag_count < len(dag_tasks):
                            # Scale down: keep only desired count
                            dag_tasks = dag_tasks[:desired_dag_count]
                        
                        uninstall_rb['task_definition_list'] = dag_tasks
                    
                    elif tasks and task_count > len(tasks):
                        # No DAG found, just duplicate first task
                        first_task = tasks[0] if tasks else {}
                        for i in range(task_count - len(tasks)):
                            new_task = copy.deepcopy(first_task)
                            new_task['uuid'] = str(uuid.uuid4())
                            tasks.append(new_task)
                    elif task_count < len(tasks):
                        # Reduce tasks
                        uninstall_rb['task_definition_list'] = tasks[:task_count]
                
                # Scale variable_list if specified
                var_path = 'options.uninstall_runbook.variable_list'
                if var_path in entity_counts:
                    var_count = entity_counts[var_path]
                    vars_list = uninstall_rb.get('variable_list', [])
                    if vars_list and var_count > len(vars_list):
                        first_var = vars_list[0] if vars_list else {}
                        for i in range(var_count - len(vars_list)):
                            new_var = copy.deepcopy(first_var)
                            new_var['uuid'] = str(uuid.uuid4())
                            vars_list.append(new_var)
                    elif var_count < len(vars_list):
                        uninstall_rb['variable_list'] = vars_list[:var_count]
                
                # Fix task target_any_local_reference to point to package
                for task in uninstall_rb.get('task_definition_list', []):
                    if 'target_any_local_reference' in task:
                        if task['target_any_local_reference'].get('kind') == 'app_package':
                            task['target_any_local_reference']['uuid'] = pkg_uuid
                
                # Always apply runbook rules to ensure DAG references are correct (even if tasks weren't scaled)
                apply_runbook_rules_to_runbook(uninstall_rb)
        
        # Fix service_local_reference_list - map to service UUIDs (one-to-one)
        if 'service_local_reference_list' in pkg and service_uuids:
            for ref_idx, ref in enumerate(pkg.get('service_local_reference_list', [])):
                # Use corresponding service UUID (one-to-one) or round-robin
                svc_uuid = service_uuids[ref_idx % len(service_uuids)] if ref_idx < len(service_uuids) else service_uuids[-1]
                ref['uuid'] = svc_uuid
    
    # 3. Fix service action_list - target_any_local_reference should point to service uuid
    #    Also generate unique action.uuid and runbook.uuid for each action
    for svc in resources.get('service_definition_list', []):
        svc_uuid = svc.get('uuid')
        if svc_uuid:
            for action in svc.get('action_list', []):
                # Generate unique UUID for the action itself
                action['uuid'] = str(uuid.uuid4())
                
                if 'runbook' in action:
                    runbook = action['runbook']
                    
                    # Generate unique UUID for action runbook
                    runbook['uuid'] = str(uuid.uuid4())
                    
                    # Scale tasks and variables if specified in entity_counts
                    task_path = 'spec.resources.service_definition_list.action_list.runbook.task_definition_list'
                    if task_path in entity_counts:
                        task_count = entity_counts[task_path]
                        tasks = runbook.get('task_definition_list', [])
                        
                        # Find DAG and EXEC tasks
                        dag_task = None
                        exec_tasks = []
                        for task in tasks:
                            if task.get('type') == 'DAG':
                                dag_task = task
                            else:
                                exec_tasks.append(task)
                        
                        if dag_task and exec_tasks:
                            desired_exec_count = max(1, task_count - 1)
                            if desired_exec_count > len(exec_tasks):
                                first_exec = exec_tasks[0]
                                for i in range(desired_exec_count - len(exec_tasks)):
                                    new_task = copy.deepcopy(first_exec)
                                    new_task['uuid'] = str(uuid.uuid4())
                                    original_name = first_exec.get('name', 'Task')
                                    new_task['name'] = f"{original_name}_{len(exec_tasks) + i + 1}"
                                    exec_tasks.append(new_task)
                            elif desired_exec_count < len(exec_tasks):
                                exec_tasks = exec_tasks[:desired_exec_count]
                            
                            runbook['task_definition_list'] = [dag_task] + exec_tasks
                    
                    # Scale variables if specified
                    var_path = 'spec.resources.service_definition_list.action_list.runbook.variable_list'
                    if var_path in entity_counts:
                        var_count = entity_counts[var_path]
                        vars_list = runbook.get('variable_list', [])
                        if vars_list and var_count > len(vars_list):
                            first_var = vars_list[0]
                            for i in range(var_count - len(vars_list)):
                                new_var = copy.deepcopy(first_var)
                                new_var['uuid'] = str(uuid.uuid4())
                                vars_list.append(new_var)
                        elif var_count < len(vars_list):
                            runbook['variable_list'] = vars_list[:var_count]
                    
                    # Apply runbook rules to update DAG references and edges
                    apply_runbook_rules_to_runbook(runbook)
                    
                    tasks = runbook.get('task_definition_list', [])
                    for task in tasks:
                        if 'target_any_local_reference' in task:
                            if task['target_any_local_reference'].get('kind') == 'app_service':
                                task['target_any_local_reference']['uuid'] = svc_uuid
    
    # 3b. Fix substrate action_list - action.uuid and runbook.uuid, scale tasks/variables
    for substrate in resources.get('substrate_definition_list', []):
        for action in substrate.get('action_list', []):
            action['uuid'] = str(uuid.uuid4())
            if 'runbook' in action:
                runbook = action['runbook']
                runbook['uuid'] = str(uuid.uuid4())
                
                # Scale tasks and variables if specified in entity_counts
                task_path = 'spec.resources.substrate_definition_list.action_list.runbook.task_definition_list'
                if task_path in entity_counts:
                    task_count = entity_counts[task_path]
                    tasks = runbook.get('task_definition_list', [])
                    
                    # Find DAG and EXEC tasks
                    dag_task = None
                    exec_tasks = []
                    for task in tasks:
                        if task.get('type') == 'DAG':
                            dag_task = task
                        else:
                            exec_tasks.append(task)
                    
                    if dag_task and exec_tasks:
                        desired_exec_count = max(1, task_count - 1)
                        if desired_exec_count > len(exec_tasks):
                            first_exec = exec_tasks[0]
                            for i in range(desired_exec_count - len(exec_tasks)):
                                new_task = copy.deepcopy(first_exec)
                                new_task['uuid'] = str(uuid.uuid4())
                                original_name = first_exec.get('name', 'Task')
                                new_task['name'] = f"{original_name}_{len(exec_tasks) + i + 1}"
                                exec_tasks.append(new_task)
                        elif desired_exec_count < len(exec_tasks):
                            exec_tasks = exec_tasks[:desired_exec_count]
                        
                        runbook['task_definition_list'] = [dag_task] + exec_tasks
                
                # Scale variables if specified
                var_path = 'spec.resources.substrate_definition_list.action_list.runbook.variable_list'
                if var_path in entity_counts:
                    var_count = entity_counts[var_path]
                    vars_list = runbook.get('variable_list', [])
                    if vars_list and var_count > len(vars_list):
                        first_var = vars_list[0]
                        for i in range(var_count - len(vars_list)):
                            new_var = copy.deepcopy(first_var)
                            new_var['uuid'] = str(uuid.uuid4())
                            vars_list.append(new_var)
                    elif var_count < len(vars_list):
                        runbook['variable_list'] = vars_list[:var_count]
                
                # Always apply runbook rules to ensure DAG references are correct
                apply_runbook_rules_to_runbook(runbook)
    
    # 3c. Fix app_profile action_list - action.uuid and runbook.uuid
    for profile in resources.get('app_profile_list', []):
        for action in profile.get('action_list', []):
            action['uuid'] = str(uuid.uuid4())
            if 'runbook' in action:
                action['runbook']['uuid'] = str(uuid.uuid4())
                # Apply runbook rules to ensure DAG references are correct
                apply_runbook_rules_to_runbook(action['runbook'])
        
        # 3d. Fix deployment action_list - action.uuid and runbook.uuid
        for deployment in profile.get('deployment_create_list', []):
            for action in deployment.get('action_list', []):
                action['uuid'] = str(uuid.uuid4())
                if 'runbook' in action:
                    action['runbook']['uuid'] = str(uuid.uuid4())
                    # Apply runbook rules to ensure DAG references are correct
                    apply_runbook_rules_to_runbook(action['runbook'])
    
    # 4. Fix deployment references - substrate and package references
    deployment_idx = 0
    for profile in resources.get('app_profile_list', []):
        for dep in profile.get('deployment_create_list', []):
            # Fix substrate_local_reference - one-to-one mapping
            if 'substrate_local_reference' in dep and substrate_uuids:
                sub_uuid = substrate_uuids[deployment_idx % len(substrate_uuids)] if deployment_idx < len(substrate_uuids) else substrate_uuids[-1]
                dep['substrate_local_reference']['uuid'] = sub_uuid
            
            # Fix package_local_reference_list - one-to-one mapping
            if 'package_local_reference_list' in dep and package_uuids:
                for ref_idx, pkg_ref in enumerate(dep.get('package_local_reference_list', [])):
                    # Map to corresponding package UUID
                    pkg_uuid = package_uuids[deployment_idx % len(package_uuids)] if deployment_idx < len(package_uuids) else package_uuids[-1]
                    pkg_ref['uuid'] = pkg_uuid
            
            deployment_idx += 1
    
    # 5. Fix client_attrs - map deployment UUIDs (skip for single_vm)
    if blueprint_type != 'single_vm':
        deployments = []
        for profile in resources.get('app_profile_list', []):
            for dep in profile.get('deployment_create_list', []):
                if dep.get('uuid'):
                    deployments.append(dep['uuid'])
        
        if deployments:
            # Rebuild client_attrs with deployment UUIDs
            new_client_attrs = {}
            for i, dep_uuid in enumerate(deployments):
                # Position each deployment in UI
                new_client_attrs[dep_uuid] = {"x": 61 + (i * 200), "y": 334}
            resources['client_attrs'] = new_client_attrs
    
    return data


def apply_profile_options(data: Any, profile_options: Dict[str, int]) -> Any:
    """
    Apply app profile options to control optional fields in the generated payload.
    
    Args:
        data: The payload data
        profile_options: Dict with counts for optional features:
            - action_list: Number of profile actions (0 = clear to empty [])
            - snapshot_config_list: Number of snapshot configs (0 = remove field entirely)
            - restore_config_list: Number of restore configs (0 = remove field entirely)
            - patch_list: Number of patch configs (0 = remove field entirely)
    """
    if not isinstance(data, dict) or 'spec' not in data:
        return data
    
    resources = data.get('spec', {}).get('resources', {})
    if not resources:
        return data
    
    app_profiles = resources.get('app_profile_list', [])
    
    for profile in app_profiles:
        # Handle action_list - if 0, clear all actions (set to empty array)
        action_count = profile_options.get('action_list', 0)
        if action_count == 0:
            # Clear action_list to empty array (profile actions are optional)
            profile['action_list'] = []
        # If action_count > 0, keep existing actions (they were scaled from original)
        
        # Handle snapshot_config_list - if 0, remove the field entirely
        snapshot_count = profile_options.get('snapshot_config_list', 0)
        if snapshot_count == 0:
            if 'snapshot_config_list' in profile:
                del profile['snapshot_config_list']
        # If > 0, keep existing (scaled from original)
        
        # Handle restore_config_list - if 0, remove the field entirely
        restore_count = profile_options.get('restore_config_list', 0)
        if restore_count == 0:
            if 'restore_config_list' in profile:
                del profile['restore_config_list']
        # If > 0, keep existing (scaled from original)
        
        # Handle patch_list - if 0, remove the field entirely
        patch_count = profile_options.get('patch_list', 0)
        if patch_count == 0:
            if 'patch_list' in profile:
                del profile['patch_list']
        # If > 0, keep existing (scaled from original)
    
    return data


def apply_internal_references(data: Any, default_rules_data: Dict) -> Any:
    """
    Apply internal reference mappings within entities.
    For example: package_definition_list.options.install_runbook.uuid should match package_definition_list.uuid
    """
    internal_mappings = default_rules_data.get('internal_reference_mappings', [])
    
    for mapping in internal_mappings:
        mapping_type = mapping.get('type', '')
        entity_path = mapping.get('entity', '')
        
        if mapping_type == 'self_reference':
            # Copy entity's own UUID to nested fields
            source_field = mapping.get('source_field', 'uuid')
            target_fields = mapping.get('target_fields', [])
            
            data = apply_self_reference_mapping(data, entity_path, source_field, target_fields)
        
        elif mapping_type == 'first_item_reference':
            # Use first item's UUID from a list for a reference field
            source_path = mapping.get('source_path', '')
            target_path = mapping.get('target_path', '')
            
            data = apply_first_item_reference(data, entity_path, source_path, target_path)
    
    return data


def apply_self_reference_mapping(data: Any, entity_path: str, source_field: str, target_fields: List[str]) -> Any:
    """
    For each item in entity_path, copy source_field value to all target_fields.
    Example: package.uuid -> package.options.install_runbook.uuid
    """
    parts = entity_path.split('.')
    
    def process_at_path(obj, remaining_parts):
        if not remaining_parts:
            if isinstance(obj, list):
                result = []
                for item in obj:
                    if isinstance(item, dict) and source_field in item:
                        source_value = item[source_field]
                        item = copy.deepcopy(item)
                        # Set all target fields to source value
                        for target in target_fields:
                            set_nested_value(item, target, source_value)
                        result.append(item)
                    else:
                        result.append(item)
                return result
            return obj
        
        part = remaining_parts[0]
        rest = remaining_parts[1:]
        
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k == part:
                    result[k] = process_at_path(v, rest)
                else:
                    result[k] = process_at_path(v, remaining_parts)
            return result
        elif isinstance(obj, list):
            return [process_at_path(item, remaining_parts) for item in obj]
        else:
            return obj
    
    return process_at_path(data, parts)


def apply_first_item_reference(data: Any, entity_path: str, source_path: str, target_path: str) -> Any:
    """
    For each item in entity_path, get first item from source_path list and copy its UUID to target_path.
    Example: install_runbook.task_definition_list[0].uuid -> install_runbook.main_task_local_reference.uuid
    """
    parts = entity_path.split('.')
    
    def process_at_path(obj, remaining_parts):
        if not remaining_parts:
            if isinstance(obj, list):
                result = []
                for item in obj:
                    if isinstance(item, dict):
                        item = copy.deepcopy(item)
                        # Get first item UUID from source path
                        source_list = get_nested_value(item, source_path.rsplit('.', 1)[0] if '.' in source_path else source_path)
                        if isinstance(source_list, list) and len(source_list) > 0:
                            first_item = source_list[0]
                            if isinstance(first_item, dict) and 'uuid' in first_item:
                                first_uuid = first_item['uuid']
                                set_nested_value(item, target_path, first_uuid)
                        result.append(item)
                    else:
                        result.append(item)
                return result
            return obj
        
        part = remaining_parts[0]
        rest = remaining_parts[1:]
        
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if k == part:
                    result[k] = process_at_path(v, rest)
                else:
                    result[k] = process_at_path(v, remaining_parts)
            return result
        elif isinstance(obj, list):
            return [process_at_path(item, remaining_parts) for item in obj]
        else:
            return obj
    
    return process_at_path(data, parts)


def get_nested_value(obj: Any, path: str) -> Any:
    """Get a value from a nested path like 'options.install_runbook.task_definition_list'"""
    parts = path.split('.')
    current = obj
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def set_nested_value(obj: Any, path: str, value: Any) -> None:
    """Set a value at a nested path like 'options.install_runbook.uuid'"""
    parts = path.split('.')
    current = obj
    for part in parts[:-1]:
        if isinstance(current, dict):
            if part not in current:
                current[part] = {}
            current = current[part]
        else:
            return
    if isinstance(current, dict):
        current[parts[-1]] = value


def apply_runbook_specific_fixes(data: Any, entity_counts: Dict[str, int], task_execution: str = 'auto') -> Any:
    """
    Apply runbook-specific fixes after scaling.
    Handles task scaling with proper DAG references.
    
    Args:
        data: The payload data
        entity_counts: Entity counts for scaling
        task_execution: 'parallel', 'series', or 'auto' (auto-detect from payload)
    """
    if not isinstance(data, dict) or 'spec' not in data:
        return data
    
    resources = data.get('spec', {}).get('resources', {})
    runbook = resources.get('runbook', {})
    
    if not runbook:
        return data
    
    task_list = runbook.get('task_definition_list', [])
    if not task_list:
        return data
    
    # Find the DAG task (type == "DAG") and EXEC tasks
    dag_task = None
    exec_tasks = []
    
    for task in task_list:
        if task.get('type') == 'DAG':
            dag_task = task
        else:
            exec_tasks.append(task)
    
    if not dag_task:
        return data
    
    # Determine task execution mode
    # 'auto' = auto-detect from original payload (if has edges, use series; otherwise parallel)
    # 'parallel' = explicitly parallel (no edges, all tasks run simultaneously)
    # 'series' = explicitly series (edges linking tasks sequentially)
    original_edges = dag_task.get('attrs', {}).get('edges', [])
    if task_execution == 'auto':
        # Auto-detect: If original has edges, use series mode; otherwise parallel
        if original_edges and len(original_edges) > 0:
            task_execution = 'series'
        else:
            task_execution = 'parallel'
    # If 'parallel' or 'series' is explicitly set, use that value directly
    
    # Get the desired task count from entity_counts
    task_path = 'spec.resources.runbook.task_definition_list'
    desired_count = entity_counts.get(task_path, len(task_list))
    
    # The desired count includes DAG + EXEC tasks
    # We want (desired_count - 1) EXEC tasks (since DAG is always 1)
    desired_exec_count = max(1, desired_count - 1)
    
    if len(exec_tasks) > 0 and desired_exec_count > 0:
        first_exec_task = exec_tasks[0]
        new_exec_tasks = []
        
        for i in range(desired_exec_count):
            new_task = copy.deepcopy(first_exec_task)
            new_task['uuid'] = str(uuid.uuid4())
            
            # Update task name with suffix
            original_name = first_exec_task.get('name', 'Task')
            new_task['name'] = f"{original_name}_{i + 1}" if desired_exec_count > 1 else original_name
            
            new_exec_tasks.append(new_task)
        
        # Update DAG's child_tasks_local_reference_list
        dag_task['child_tasks_local_reference_list'] = [
            {'kind': 'app_task', 'uuid': task['uuid']}
            for task in new_exec_tasks
        ]
        
        # Create edges based on task_execution mode
        if task_execution == 'series' and len(new_exec_tasks) > 1:
            # Series: Create edges linking tasks in sequence (Task1 -> Task2 -> Task3...)
            edges = []
            for i in range(len(new_exec_tasks) - 1):
                edge = {
                    'from_task_reference': {
                        'kind': 'app_task',
                        'uuid': new_exec_tasks[i]['uuid']
                    },
                    'to_task_reference': {
                        'kind': 'app_task',
                        'uuid': new_exec_tasks[i + 1]['uuid']
                    },
                    'uuid': str(uuid.uuid4())
                }
                edges.append(edge)
            
            if 'attrs' not in dag_task:
                dag_task['attrs'] = {}
            dag_task['attrs']['edges'] = edges
        else:
            # Parallel: No edges (all tasks run at the same time)
            if 'attrs' not in dag_task:
                dag_task['attrs'] = {}
            dag_task['attrs']['edges'] = []
        
        # Rebuild task_definition_list: DAG first, then EXEC tasks
        runbook['task_definition_list'] = [dag_task] + new_exec_tasks
        
        # Update main_task_local_reference to point to DAG
        if 'main_task_local_reference' in runbook:
            runbook['main_task_local_reference']['uuid'] = dag_task['uuid']
    
    # Always generate new UUID for the runbook itself
    if 'uuid' in runbook:
        runbook['uuid'] = str(uuid.uuid4())
    
    # Also regenerate DAG task UUID
    if dag_task and 'uuid' in dag_task:
        new_dag_uuid = str(uuid.uuid4())
        dag_task['uuid'] = new_dag_uuid
        # Update main_task_local_reference to match
        if 'main_task_local_reference' in runbook:
            runbook['main_task_local_reference']['uuid'] = new_dag_uuid
    
    # Always update metadata.uuid and spec.name for runbooks
    data = update_metadata_uuid(data)
    data = update_spec_name(data)
    
    return data


def restore_preserved_fields(original: Any, scaled: Any, preserve_fields: List[Dict]) -> Any:
    """
    Restore fields that should not be changed (user input fields).
    """
    for field_config in preserve_fields:
        path = field_config.get('path', '')
        if path:
            original_value = get_value_at_path(original, path)
            if original_value is not None:
                scaled = set_value_at_path(scaled, path, original_value)
    
    return scaled


def get_value_at_path(data: Any, path: str) -> Any:
    """Get value at a path, handling arrays by returning all values."""
    parts = path.split('.')
    
    def traverse(obj, remaining_parts):
        if not remaining_parts:
            return obj
        
        part = remaining_parts[0]
        rest = remaining_parts[1:]
        
        if isinstance(obj, dict):
            if part in obj:
                return traverse(obj[part], rest)
            return None
        elif isinstance(obj, list):
            results = []
            for item in obj:
                result = traverse(item, remaining_parts)
                if result is not None:
                    if isinstance(result, list):
                        results.extend(result)
                    else:
                        results.append(result)
            return results if results else None
        return None
    
    return traverse(data, parts)


def set_value_at_path(data: Any, path: str, value: Any) -> Any:
    """
    Set value at a path, handling arrays.
    For preserved fields, we use the FIRST original value for ALL items.
    This ensures user-input fields (like account_uuid) are consistent across scaled items.
    """
    parts = path.split('.')
    # Use first value if value is a list (for consistency across scaled items)
    first_value = value[0] if isinstance(value, list) and len(value) > 0 else value
    
    def traverse(obj, remaining_parts):
        if not remaining_parts:
            return first_value
        
        part = remaining_parts[0]
        rest = remaining_parts[1:]
        
        if isinstance(obj, dict):
            result = copy.deepcopy(obj)  # Start with a copy
            if part in obj:
                if not rest:
                    # This is the target field - set to first_value
                    result[part] = first_value
                else:
                    # Continue traversing deeper
                    result[part] = traverse(obj[part], rest)
            return result
        elif isinstance(obj, list):
            # Apply to all items in the array
            return [traverse(item, remaining_parts) for item in obj]
        else:
            return obj
    
    return traverse(data, parts)


def scale_payload_with_rules(data: Any, entity_counts: Dict[str, int], mapping_rules: List[Dict[str, Any]], api_type: str = 'blueprint', task_execution: str = 'parallel', blueprint_type: str = 'multi_vm', profile_options: Dict[str, int] = None, include_guest_customization: bool = False) -> Any:
    """Scale the payload and apply mapping rules.
    
    Args:
        data: The payload to scale
        entity_counts: Dictionary of entity path -> count
        mapping_rules: List of transformation rules
        api_type: 'blueprint', 'runbook', or 'app'
        task_execution: For runbooks - 'parallel' or 'series'
        blueprint_type: For blueprints - 'single_vm' or 'multi_vm'
        profile_options: Optional dict with app profile features (action_list, snapshot_config_list, etc.)
    """
    if profile_options is None:
        profile_options = {}
    # Store original for preserving certain fields
    original_data = copy.deepcopy(data)
    
    # Load default rules configuration
    default_rules_data = load_default_rules(api_type)
    
    # For Blueprint: Calculate entity counts based on correct relationships
    # The relationship is: app_profiles -> deployments -> substrates/packages
    # Total substrates = app_profile_count × deployments_per_profile
    # Total packages = app_profile_count × deployments_per_profile
    # Services can be independent
    if api_type == 'blueprint':
        # Get user-specified counts
        app_profile_count = entity_counts.get('spec.resources.app_profile_list', 1)
        deployments_per_profile = entity_counts.get('spec.resources.app_profile_list.deployment_create_list', 1)
        
        # For single_vm, force to 1 profile with 1 deployment and 1 service
        if blueprint_type == 'single_vm':
            app_profile_count = 1
            deployments_per_profile = 1
            entity_counts['spec.resources.service_definition_list'] = 1
            entity_counts['spec.resources.app_profile_list'] = 1
            entity_counts['spec.resources.app_profile_list.deployment_create_list'] = 1
        
        # Calculate total deployments across all profiles
        total_deployments = app_profile_count * deployments_per_profile
        
        # Substrates and Packages = total deployments (each deployment needs one of each)
        entity_counts['spec.resources.substrate_definition_list'] = total_deployments
        entity_counts['spec.resources.package_definition_list'] = total_deployments
        
        # Keep credential at 1 (or user-specified if they explicitly set it)
        if 'spec.resources.credential_definition_list' not in entity_counts:
            entity_counts['spec.resources.credential_definition_list'] = 1
    
    # For runbooks, exclude task_definition_list from generic scaling
    # (handled specially in apply_runbook_specific_fixes)
    if api_type == 'runbook':
        entity_counts_for_scaling = {
            k: v for k, v in entity_counts.items()
            if 'task_definition_list' not in k
        }
    else:
        entity_counts_for_scaling = entity_counts
    
    # Scale the payload
    scaled = scale_payload(data, entity_counts_for_scaling)
    
    # Apply API-type-specific fixes FIRST (before name suffixes)
    if api_type == 'blueprint':
        # Load runbook default rules to apply to blueprint runbooks
        runbook_rules = load_default_rules('runbook')
        
        # Blueprint: credential refs, package runbook refs, client_attrs, etc.
        scaled = apply_blueprint_specific_fixes(scaled, blueprint_type, entity_counts, runbook_rules)
        # Apply profile options (remove or keep optional fields based on user selection)
        scaled = apply_profile_options(scaled, profile_options)
        # Handle guest_customization based on toggle
        if not include_guest_customization:
            # Set guest_customization to null in all substrates
            resources = scaled.get('spec', {}).get('resources', {})
            for substrate in resources.get('substrate_definition_list', []):
                if 'create_spec' in substrate and 'resources' in substrate['create_spec']:
                    substrate['create_spec']['resources']['guest_customization'] = None
    elif api_type == 'runbook':
        # Runbook: task scaling with DAG reference updates
        # This handles task scaling specially to preserve DAG structure
        scaled = apply_runbook_specific_fixes(scaled, entity_counts, task_execution)
    
    # Always update metadata.uuid with a new UUID
    scaled = update_metadata_uuid(scaled)
    
    # Update spec.name with unique suffix
    scaled = update_spec_name(scaled)
    
    # Apply name suffixes to all scaled entities (skip for runbook tasks - already named)
    scaled = apply_name_suffix_to_entities(scaled, entity_counts_for_scaling)
    
    # Apply reference mapping rules (cross-entity references)
    ref_rules = [r for r in mapping_rules if r.get('type') == 'reference_mapping']
    # Skip filter rules for action_list - they cause issues
    other_rules = [r for r in mapping_rules if r.get('type') != 'reference_mapping' and r.get('type') != 'filter']
    
    for rule in ref_rules:
        scaled = apply_reference_mapping_rule(scaled, rule)
    
    # Apply other rules
    for rule in other_rules:
        rule_type = rule.get('type', '')
        
        if rule_type == 'use_single':
            scaled = apply_single_source_rule(scaled, rule)
        elif rule_type == 'clone':
            scaled = apply_clone_rule(scaled, rule)
        elif rule_type == 'set_value':
            scaled = apply_set_value_rule(scaled, rule)
        elif rule_type == 'keep_first':
            scaled = apply_keep_first_rule(scaled, rule)
        elif rule_type == 'remove_field':
            scaled = apply_remove_field_rule(scaled, rule)
    
    # Restore preserved fields (user input fields that shouldn't change)
    preserve_fields = default_rules_data.get('preserve_fields', [])
    scaled = restore_preserved_fields(original_data, scaled, preserve_fields)
    
    # FINAL STEP: Regenerate ALL entity UUIDs to ensure complete uniqueness
    # This prevents "entity already exists" errors when creating new resources
    if api_type == 'blueprint':
        scaled = regenerate_all_entity_uuids(scaled)
    
    # CRITICAL: Fix main_task_local_reference.uuid = task_definition_list[0].uuid
    # This MUST be called AFTER all UUID regeneration to ensure mapping is correct
    # This applies to both blueprints (after regenerate_all_entity_uuids) 
    # and runbooks (after apply_runbook_specific_fixes which may regenerate DAG UUIDs)
    fix_all_runbooks_in_object(scaled)
    
    return scaled

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test-dropdowns')
def test_dropdowns():
    """Test page for enhanced dropdowns"""
    return open('/Users/mohan.as1/Documents/payload-scaler/test_dropdowns.html').read()

@app.route('/debug-project')
def debug_project():
    """Debug page for project selection"""
    return open('/Users/mohan.as1/Documents/payload-scaler/debug_project_selection.html').read()


@app.route('/api/test/project-resources')
def test_project_resources():
    """Test endpoint to verify project resource structure"""
    try:
        # Get a sample project from the live API
        import requests
        from requests.auth import HTTPBasicAuth
        
        session = requests.Session()
        session.auth = HTTPBasicAuth('admin', 'Nutanix.123')
        session.headers = {'Content-Type': 'application/json'}
        session.verify = False
        
        api_url = build_api_url('https://iam.nconprem-10-53-58-35.ccpnx.com/', 'dm', 'api/nutanix/v3/projects/list')
        
        response = session.post(
            api_url,
            json={"length": 1, "offset": 0, "kind": "project"},
            timeout=30
        )
        
        if response.status_code == 200:
            projects_data = response.json()
            if projects_data.get('entities'):
                project = projects_data['entities'][0]
                resources = project.get('spec', {}).get('resources', {})
                
                return jsonify({
                    'success': True,
                    'project_name': project.get('spec', {}).get('name'),
                    'project_uuid': project.get('metadata', {}).get('uuid'),
                    'resources': {
                        'accounts': len(resources.get('account_reference_list', [])),
                        'clusters': len(resources.get('cluster_reference_list', [])),
                        'environments': len(resources.get('environment_reference_list', [])),
                        'networks': len(resources.get('external_network_list', [])),
                        'subnets': len(resources.get('subnet_reference_list', [])),
                        'account_details': resources.get('account_reference_list', []),
                        'cluster_details': resources.get('cluster_reference_list', []),
                        'environment_details': resources.get('environment_reference_list', []),
                        'network_details': resources.get('external_network_list', []),
                        'subnet_details': resources.get('subnet_reference_list', [])
                    }
                })
        
        return jsonify({'error': 'No projects found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/perf-child')
def perf_child():
    """Child tab for performance testing - receives BroadcastChannel messages."""
    target_url = request.args.get('url', '')
    tab_id = request.args.get('tabId', '1')
    return render_template('perf_child.html', target_url=target_url, tab_id=tab_id)


# --- Section 1: Rules Management APIs ---

@app.route('/api/rules/analyze', methods=['POST'])
def analyze_for_rules():
    """
    Analyze a payload to detect scalable entities.
    Used in Section 1: Generate New Payload Rules
    """
    try:
        payload_data = request.json.get('payload')
        api_type = request.json.get('api_type', 'blueprint')
        # api_url is received but not used in analysis (used for identification only)
        _ = request.json.get('api_url', '')
        
        if not payload_data:
            return jsonify({'error': 'No payload provided'}), 400
        
        if isinstance(payload_data, str):
            payload_data = json.loads(payload_data)
        
        # Auto-detect api_type from payload if metadata.kind exists
        if isinstance(payload_data, dict):
            metadata_kind = payload_data.get('metadata', {}).get('kind', '')
            if metadata_kind == 'runbook':
                api_type = 'runbook'
            elif metadata_kind == 'app':
                api_type = 'app'
            elif metadata_kind == 'blueprint':
                api_type = 'blueprint'
        
        print(f"[DEBUG] analyze_for_rules - api_type: {api_type}")
        
        entities = find_entities_in_payload(payload_data, api_type=api_type)
        print(f"[DEBUG] Found {len(entities)} entities: {list(entities.keys())}")
        id_values = collect_all_id_values(payload_data)
        reference_map = find_references(payload_data, id_values)
        
        entities_list = []
        for path, info in entities.items():
            entity_references = []
            for id_field in info.get('id_fields', []):
                id_path = id_field['path']
                if id_path in reference_map:
                    entity_references.append({
                        'field': id_field['field'],
                        'referenced_by': reference_map[id_path]
                    })
            
            entities_list.append({
                'path': path,
                'type': info['type'],
                'current_count': info['current_count'],
                'sample': json.dumps(info['sample'], indent=2) if info['sample'] else None,
                'id_fields': info.get('id_fields', []),
                'references': entity_references,
                'auto_linked': info.get('auto_linked', False)
            })
        
        response_data = {
            'success': True,
            'entities': entities_list,
            'original_payload': payload_data,
            'scalable_entity_paths': list(entities.keys()),
            'reference_map': {k: v for k, v in reference_map.items()},
            'detected_api_type': api_type  # Return detected type so frontend can update dropdown
        }
        
        # Log API request/response
        log_api_request_response(
            api_name="scalar_rules_analyze",
            endpoint="/api/rules/analyze",
            method="POST",
            request_data=request.json,
            response_data=response_data,
            status_code=200
        )
        
        return jsonify(response_data)
    
    except json.JSONDecodeError as e:
        error_response = {'error': f'Invalid JSON: {str(e)}'}
        log_api_request_response(
            api_name="scalar_rules_analyze",
            endpoint="/api/rules/analyze",
            method="POST",
            request_data=request.json,
            response_data=error_response,
            status_code=400,
            error=str(e)
        )
        return jsonify(error_response), 400
    except Exception as e:
        error_response = {'error': f'Error analyzing payload: {str(e)}'}
        log_api_request_response(
            api_name="scalar_rules_analyze",
            endpoint="/api/rules/analyze",
            method="POST",
            request_data=request.json,
            response_data=error_response,
            status_code=500,
            error=str(e)
        )
        return jsonify(error_response), 500


@app.route('/api/rules/preview', methods=['POST'])
def preview_with_rules():
    """
    Generate a preview payload using temporary entity counts and rules.
    Entity counts are NOT persisted - only for preview.
    """
    try:
        original_payload = request.json.get('original_payload')
        entity_counts = request.json.get('entity_counts', {})
        rules = request.json.get('rules', [])
        api_type = request.json.get('api_type', 'blueprint')
        task_execution = request.json.get('task_execution', 'parallel')  # For runbooks: 'parallel' or 'series'
        blueprint_type = request.json.get('blueprint_type', 'multi_vm')  # For blueprints: 'single_vm' or 'multi_vm'
        profile_options = request.json.get('profile_options', {})  # App profile optional features
        
        if not original_payload:
            return jsonify({'error': 'No original payload provided'}), 400
        
        counts = {k: int(v) for k, v in entity_counts.items() if v}
        scaled_payload = scale_payload_with_rules(original_payload, counts, rules, api_type, task_execution, blueprint_type, profile_options)
        
        response_data = {
            'success': True,
            'preview_payload': scaled_payload,
            'formatted_payload': json.dumps(scaled_payload, indent=2)
        }
        
        # Log API request/response
        log_api_request_response(
            api_name="scalar_rules_preview",
            endpoint="/api/rules/preview",
            method="POST",
            request_data=request.json,
            response_data=response_data,
            status_code=200
        )
        
        return jsonify(response_data)
    
    except Exception as e:
        error_response = {'error': f'Error generating preview: {str(e)}'}
        
        # Log API error
        log_api_request_response(
            api_name="scalar_rules_preview",
            endpoint="/api/rules/preview",
            method="POST",
            request_data=request.json,
            response_data=error_response,
            status_code=500,
            error=str(e)
        )
        
        return jsonify(error_response), 500


@app.route('/api/rules/save', methods=['POST'])
def save_rules_for_api():
    """
    Save rules for an entity.
    NOTE: Entity counts are NOT saved - only rules!
    """
    try:
        api_url = request.json.get('api_url', '')
        api_type = request.json.get('api_type', 'blueprint')
        rules = request.json.get('rules', [])
        payload_template = request.json.get('payload_template')
        scalable_entities = request.json.get('scalable_entities', [])
        task_execution = request.json.get('task_execution', 'parallel')  # For runbooks
        save_history = request.json.get('save_history', False)  # Save previous version to history
        
        if not api_url:
            return jsonify({'error': 'Entity name is required'}), 400
        
        # Check if entity already exists and save to history if requested
        existing_rule_data = get_api_rule_set(api_url)
        if existing_rule_data and save_history:
            existing_template = load_payload_template(api_url)
            add_to_history(api_url, existing_rule_data, existing_template)
        
        save_api_rule_set(api_url, api_type, rules, payload_template, scalable_entities, task_execution)
        
        response_data = {
            'success': True,
            'message': f'Entity saved: {api_url}',
            'note': 'Entity counts are not persisted - they are runtime-only',
            'history_saved': bool(existing_rule_data and save_history)
        }
        
        # Log API request/response
        log_api_request_response(
            api_name="scalar_rules_save",
            endpoint="/api/rules/save",
            method="POST",
            request_data=request.json,
            response_data=response_data,
            status_code=200
        )
        
        return jsonify(response_data)
    
    except Exception as e:
        error_response = {'error': f'Error saving rules: {str(e)}'}
        
        # Log API error
        log_api_request_response(
            api_name="scalar_rules_save",
            endpoint="/api/rules/save",
            method="POST",
            request_data=request.json,
            response_data=error_response,
            status_code=500,
            error=str(e)
        )
        
        return jsonify(error_response), 500


@app.route('/api/rules/<path:api_url>', methods=['GET'])
def get_rules_for_api(api_url):
    """Get saved rules for a specific API URL.
    
    Query params:
        include_template: If 'true', includes the payload template in response (for undo functionality)
    """
    rule_data = get_api_rule_set(api_url)
    
    if not rule_data:
        return jsonify({'error': 'No rules found for this API'}), 404
    
    response_data = {
        'success': True,
        'api_url': api_url,
        'api_type': rule_data.get('api_type', 'blueprint'),
        'rules': rule_data.get('rules', []),
        'scalable_entities': rule_data.get('scalable_entities', []),
        'has_template': rule_data.get('has_template', False),
        'task_execution': rule_data.get('task_execution', 'parallel')  # For runbooks
    }
    
    # Include template if requested (for undo functionality)
    include_template = request.args.get('include_template', 'false').lower() == 'true'
    if include_template:
        payload_template = load_payload_template(api_url)
        if payload_template:
            response_data['payload_template'] = payload_template
    
    return jsonify(response_data)


@app.route('/api/rules/<path:api_url>', methods=['DELETE'])
def delete_rules_for_api(api_url):
    """Delete rules for a specific entity."""
    try:
        if delete_api_rule_set(api_url):
            return jsonify({'success': True, 'message': f'Entity deleted: {api_url}'})
        return jsonify({'error': 'Entity not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Error deleting entity: {str(e)}'}), 500


@app.route('/api/rules/<path:api_url>/history', methods=['GET'])
def get_entity_history(api_url):
    """Get history for an entity."""
    try:
        history = load_entity_history(api_url)
        return jsonify({
            'success': True,
            'entity_name': api_url,
            'history': history
        })
    except Exception as e:
        return jsonify({'error': f'Error loading history: {str(e)}'}), 500


@app.route('/api/rules/<path:api_url>/history/<int:version_index>', methods=['GET'])
def get_history_version_api(api_url, version_index):
    """Get a specific version from history."""
    try:
        version_data = get_history_version(api_url, version_index)
        if not version_data:
            return jsonify({'error': 'Version not found'}), 404
        
        return jsonify({
            'success': True,
            'entity_name': api_url,
            'version_index': version_index,
            'version_data': version_data
        })
    except Exception as e:
        return jsonify({'error': f'Error loading version: {str(e)}'}), 500


@app.route('/api/rules/<path:api_url>/restore/<int:version_index>', methods=['POST'])
def restore_entity_version(api_url, version_index):
    """Restore an entity from a history version."""
    try:
        if restore_from_history(api_url, version_index):
            return jsonify({
                'success': True,
                'message': f'Entity "{api_url}" restored from version {version_index + 1}'
            })
        return jsonify({'error': 'Failed to restore - version not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Error restoring version: {str(e)}'}), 500


@app.route('/api/rules', methods=['GET'])
def list_all_api_rules():
    """List all saved API rules."""
    all_rules = load_api_rules()
    
    api_list = []
    for api_url, rule_data in all_rules.items():
        api_list.append({
            'api_url': api_url,
            'api_type': rule_data.get('api_type', 'blueprint'),
            'rules_count': len(rule_data.get('rules', [])),
            'scalable_entities_count': len(rule_data.get('scalable_entities', [])),
            'has_template': rule_data.get('has_template', False),
            'task_execution': rule_data.get('task_execution', 'parallel')  # For runbooks
        })
    
    return jsonify({
        'success': True,
        'apis': api_list
    })


# --- Section 2: Entity Generation APIs ---

@app.route('/api/payload/generate', methods=['POST'])
def generate_payload_from_rules():
    """
    Generate a payload using saved rules and runtime entity counts.
    Used in Section 2: Create Entities
    """
    try:
        api_url = request.json.get('api_url', '')
        entity_counts = request.json.get('entity_counts', {})
        task_execution = request.json.get('task_execution', 'parallel')  # For runbooks
        blueprint_type = request.json.get('blueprint_type', 'multi_vm')  # For blueprints: 'single_vm' or 'multi_vm'
        profile_options = request.json.get('profile_options', {})  # App profile optional features
        include_guest_customization = request.json.get('include_guest_customization', False)  # Guest customization toggle
        live_uuids = request.json.get('live_uuids', {})  # Live UUIDs from PC
        
        if not api_url:
            return jsonify({'error': 'API URL is required'}), 400
        
        # Load saved rules for this API
        rule_data = get_api_rule_set(api_url)
        if not rule_data:
            return jsonify({'error': 'No rules found for this API. Please create rules first.'}), 404
        
        # Load payload template
        payload_template = load_payload_template(api_url)
        if not payload_template:
            return jsonify({'error': 'No payload template found for this API. Please upload a sample payload when creating rules.'}), 404
        
        # Get saved rules
        rules = rule_data.get('rules', [])
        
        # Add default rules for the API type
        api_type = rule_data.get('api_type', 'blueprint')
        default_rules_data = load_default_rules(api_type)
        default_rules = default_rules_data.get('default_rules', [])
        
        # Combine default + custom rules
        all_rules = default_rules + rules
        
        # Apply entity counts (runtime only, never persisted)
        counts = {k: int(v) for k, v in entity_counts.items() if v}
        
        # Generate scaled payload
        include_guest_customization = request.json.get('include_guest_customization', False)
        request_data = {
            'api_url': api_url,
            'entity_counts': entity_counts,
            'task_execution': task_execution,
            'blueprint_type': blueprint_type,
            'profile_options': profile_options,
            'include_guest_customization': include_guest_customization
        }
        
        try:
            scaled_payload = scale_payload_with_rules(payload_template, counts, all_rules, api_type, task_execution, blueprint_type, profile_options, include_guest_customization=include_guest_customization)
            
            # Apply live UUIDs if provided
            if live_uuids and any(live_uuids.get(key, {}).get('uuid') for key in live_uuids):
                logger.info(f"Applying live UUIDs to payload: {json.dumps(live_uuids, indent=2)}")
                
                # Log cluster details specifically
                if 'cluster' in live_uuids:
                    cluster_info = live_uuids['cluster']
                    logger.info(f"Cluster live UUID - UUID: {cluster_info.get('uuid')}, Name: '{cluster_info.get('name')}'")
                
                scaled_payload = apply_live_uuids_to_payload(scaled_payload, live_uuids)
            
            # Store response history (last 5 responses per entity)
            save_response_history(api_url, scaled_payload, entity_counts)
            
            response_data = {
                'success': True,
                'scaled_payload': scaled_payload,
                'formatted_payload': json.dumps(scaled_payload, indent=2),
                'applied_rules_count': len(all_rules)
            }
            response = jsonify(response_data)
            save_api_request_response('/api/payload/generate', 'POST', request_data, response_data, 200)
            return response
        except Exception as e:
            error_response = {'error': f'Error generating payload: {str(e)}'}
            save_api_request_response('/api/payload/generate', 'POST', request_data, error_response, 500)
            return jsonify(error_response), 500
    
    except Exception as e:
        error_response = {'error': f'Error generating payload: {str(e)}'}
        save_api_request_response('/api/payload/generate', 'POST', request.json or {}, error_response, 500)
        return jsonify(error_response), 500


@app.route('/api/payload/entities/<path:api_url>', methods=['GET'])
def get_entities_for_api(api_url):
    """
    Get scalable entities for an API URL.
    Used when selecting an API in Section 2: Create Entities
    """
    rule_data = get_api_rule_set(api_url)
    
    if not rule_data:
        return jsonify({'error': 'No rules found for this API'}), 404
    
    api_type = rule_data.get('api_type', 'blueprint')
    
    # If we have a stored template, re-analyze it for current entities
    payload_template = load_payload_template(api_url)
    
    if payload_template:
        entities = find_entities_in_payload(payload_template, api_type=api_type)
        entities_list = [
            {
                'path': path,
                'current_count': info['current_count'],
                'id_fields': info.get('id_fields', [])
            }
            for path, info in entities.items()
        ]
    else:
        # Fall back to stored scalable entities list
        entities_list = [
            {'path': path, 'current_count': 1, 'id_fields': []}
            for path in rule_data.get('scalable_entities', [])
        ]
    
    return jsonify({
        'success': True,
        'api_url': api_url,
        'entities': entities_list,
        'api_type': rule_data.get('api_type', 'blueprint'),
        'task_execution': rule_data.get('task_execution', 'parallel')  # For runbooks
    })


# --- Utility APIs ---

@app.route('/api/types', methods=['GET'])
def get_api_types():
    """Get all supported API types."""
    return jsonify({
        'success': True,
        'api_types': API_TYPES,
        'default_action_values': DEFAULT_ACTION_VALUES
    })


@app.route('/api/default-rules/<api_type>', methods=['GET'])
def get_default_rules(api_type):
    """Get default rules for an API type."""
    if api_type not in API_TYPES:
        return jsonify({'error': f'Unknown API type: {api_type}'}), 400
    
    default_rules = load_default_rules(api_type)
    return jsonify({
        'success': True,
        'api_type': api_type,
        'default_rules': default_rules.get('default_rules', []),
        'scalable_entities': default_rules.get('scalable_entities', []),
        'default_action_values': default_rules.get('default_action_values', DEFAULT_ACTION_VALUES)
    })


# Keep legacy endpoint for backward compatibility
@app.route('/api/analyze', methods=['POST'])
def analyze_payload():
    """Legacy endpoint - redirects to new analyze endpoint."""
    return analyze_for_rules()


@app.route('/api/generate', methods=['POST'])
def generate_payload():
    """Legacy endpoint for generating payload (still supports direct generation)."""
    try:
        original_payload = request.json.get('original_payload')
        entity_counts = request.json.get('entity_counts', {})
        mapping_rules = request.json.get('mapping_rules', [])
        api_type = request.json.get('api_type', 'blueprint')
        
        if not original_payload:
            return jsonify({'error': 'No original payload provided'}), 400
        
        counts = {k: int(v) for k, v in entity_counts.items() if v}
        scaled_payload = scale_payload_with_rules(original_payload, counts, mapping_rules, api_type)
        
        return jsonify({
            'success': True,
            'scaled_payload': scaled_payload,
            'formatted_payload': json.dumps(scaled_payload, indent=2)
        })
    
    except Exception as e:
        return jsonify({'error': f'Error generating payload: {str(e)}'}), 500


# ============================================================================
# PROXY ENDPOINT - For loading external URLs in iframe (bypasses X-Frame-Options)
# ============================================================================

@app.route('/proxy')
def proxy_page():
    """Proxy an external URL to bypass iframe restrictions."""
    target_url = request.args.get('url', '')
    if not target_url:
        return "No URL provided", 400
    
    try:
        print(f"[PROXY] Fetching: {target_url}")
        
        # Create a session to handle cookies
        session = requests.Session()
        
        # Make request to target URL with SSL verification disabled for internal sites
        resp = session.get(
            target_url, 
            verify=False, 
            allow_redirects=True,
            timeout=30,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        print(f"[PROXY] Status: {resp.status_code}, URL after redirects: {resp.url}")
        
        # Get content type
        content_type = resp.headers.get('Content-Type', 'text/html')
        
        # For HTML content, rewrite relative URLs to use proxy
        content = resp.content
        if 'text/html' in content_type:
            # Decode content
            try:
                html = resp.text
                
                # Get base URL for rewriting relative paths
                parsed = urlparse(target_url)
                base_url = f"{parsed.scheme}://{parsed.netloc}"
                
                # Inject base tag to handle relative URLs
                base_tag = f'<base href="{base_url}/">'
                if '<head>' in html:
                    html = html.replace('<head>', f'<head>{base_tag}', 1)
                elif '<HEAD>' in html:
                    html = html.replace('<HEAD>', f'<HEAD>{base_tag}', 1)
                else:
                    html = base_tag + html
                
                content = html.encode('utf-8')
            except:
                pass
        
        # Create response without restrictive headers
        excluded_headers = [
            'content-encoding', 'content-length', 'transfer-encoding', 
            'connection', 'x-frame-options', 'content-security-policy',
            'x-content-type-options', 'strict-transport-security'
        ]
        headers = [(name, value) for name, value in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        
        response = Response(content, resp.status_code, headers)
        response.headers['Content-Type'] = content_type
        return response
        
    except requests.exceptions.SSLError as e:
        print(f"[PROXY] SSL Error: {e}")
        return f"<html><body><h2>SSL Error</h2><p>Cannot connect to {target_url}</p><pre>{str(e)}</pre></body></html>", 502
    except requests.exceptions.ConnectionError as e:
        print(f"[PROXY] Connection Error: {e}")
        return f"<html><body><h2>Connection Error</h2><p>Cannot connect to {target_url}</p><pre>{str(e)}</pre></body></html>", 502
    except requests.exceptions.Timeout as e:
        print(f"[PROXY] Timeout: {e}")
        return f"<html><body><h2>Timeout</h2><p>Timeout connecting to {target_url}</p></body></html>", 504
    except Exception as e:
        print(f"[PROXY] Error: {e}")
        import traceback
        traceback.print_exc()
        return f"<html><body><h2>Error</h2><p>{str(e)}</p></body></html>", 500


# ============================================================================
# PLAYWRIGHT MIRROR MODE - Main browser + mirrored child browsers
# ============================================================================

import threading
import time
from queue import Queue
import asyncio

# Global state for mirror mode
mirror_state = {
    'is_running': False,
    'main_page': None,       # Main Playwright page
    'child_pages': [],       # List of child Playwright pages  
    'browsers': [],          # Browser instances
    'playwright': None,
    'action_queue': [],      # Queue of actions to mirror
    'log': [],
    'config': {},
    'stop_requested': False,
    'metrics': {
        'actions_mirrored': 0,
        'errors': 0,
        'latencies': []
    }
}
mirror_lock = threading.Lock()

def log_mirror_event(event_type: str, message: str, session_id: str = None):
    """Log a mirror mode event."""
    with mirror_lock:
        entry = {
            'time': time.strftime('%H:%M:%S'),
            'timestamp': time.time(),
            'type': event_type,
            'message': message,
            'session_id': session_id
        }
        mirror_state['log'].insert(0, entry)
        if len(mirror_state['log']) > 200:
            mirror_state['log'] = mirror_state['log'][:200]
        print(f"[MIRROR] [{event_type}] {message}")

def start_mirror_browsers(config: dict):
    """Start main browser + child browsers for mirror mode."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log_mirror_event('ERROR', 'Playwright not installed. Run: pip install playwright && playwright install chromium')
        with mirror_lock:
            mirror_state['is_running'] = False
        return
    
    target_url = config.get('url', '')
    num_children = config.get('num_children', 2)
    headless_children = config.get('headless_children', True)
    ignore_ssl = config.get('ignore_ssl', True)
    
    try:
        log_mirror_event('INIT', f'Starting mirror mode: 1 main + {num_children} child browsers')
        
        p = sync_playwright().start()
        
        with mirror_lock:
            mirror_state['playwright'] = p
        
        # Launch main browser (always visible)
        log_mirror_event('LAUNCH', 'Launching main browser (visible)')
        main_browser = p.chromium.launch(headless=False)
        main_context = main_browser.new_context(
            ignore_https_errors=ignore_ssl,
            viewport={'width': 1280, 'height': 800}
        )
        main_page = main_context.new_page()
        
        with mirror_lock:
            mirror_state['browsers'].append(main_browser)
            mirror_state['main_page'] = main_page
        
        # Navigate main browser
        log_mirror_event('NAV', f'Main browser navigating to {target_url}')
        try:
            main_page.goto(target_url, wait_until='domcontentloaded', timeout=60000)
            log_mirror_event('LOADED', 'Main browser loaded')
        except Exception as e:
            log_mirror_event('WARN', f'Main browser load warning: {str(e)[:80]}')
        
        # Launch child browsers
        child_pages_list = []
        for i in range(num_children):
            if mirror_state.get('stop_requested'):
                break
            
            log_mirror_event('LAUNCH', f'Launching child browser {i+1}', str(i+1))
            
            child_browser = p.chromium.launch(headless=headless_children)
            child_context = child_browser.new_context(
                ignore_https_errors=ignore_ssl,
                viewport={'width': 1280, 'height': 800}
            )
            child_page = child_context.new_page()
            
            # Navigate child to same URL
            try:
                child_page.goto(target_url, wait_until='domcontentloaded', timeout=60000)
                log_mirror_event('LOADED', f'Child {i+1} loaded', str(i+1))
            except Exception as e:
                log_mirror_event('WARN', f'Child {i+1} load warning: {str(e)[:80]}', str(i+1))
            
            child_pages_list.append(child_page)
            
            with mirror_lock:
                mirror_state['browsers'].append(child_browser)
                mirror_state['child_pages'].append({
                    'id': i + 1,
                    'page': child_page,
                    'status': 'ready'
                })
        
        log_mirror_event('READY', f'Mirror mode ready: 1 main + {len(child_pages_list)} children')
        log_mirror_event('INFO', 'Interact with the main browser. Actions are mirrored via CDP events.')
        
        # Use CDP to expose a function for action mirroring
        # Inject script that uses window.mirrorAction to queue actions
        setup_cdp_mirroring(main_page, child_pages_list)
        
        # Keep running and process mirrored actions
        while not mirror_state.get('stop_requested'):
            time.sleep(0.1)
            # Process queued actions from CDP
            process_action_queue_direct(child_pages_list)
        
    except Exception as e:
        log_mirror_event('ERROR', f'Mirror mode failed: {str(e)[:150]}')
        import traceback
        traceback.print_exc()
    
    finally:
        cleanup_mirror_browsers()

def setup_cdp_mirroring(main_page, child_pages):
    """Setup CDP-based action mirroring using exposed function."""
    
    # Expose a Python function to the page that queues actions
    def mirror_action(action_data):
        with mirror_lock:
            mirror_state['action_queue'].append(action_data)
        return True
    
    try:
        main_page.expose_function('__mirrorAction', mirror_action)
        log_mirror_event('CDP', 'Exposed mirror function to main page')
    except Exception as e:
        log_mirror_event('WARN', f'Could not expose function: {str(e)[:60]}')
    
    # Inject the capture script that uses the exposed function
    capture_script = """
    (function() {
        console.log('[Mirror] Initializing action capture...');
        
        let lastAction = 0;
        const minDelay = 50;
        
        function sendAction(action) {
            const now = Date.now();
            if (now - lastAction < minDelay) return;
            lastAction = now;
            
            if (typeof window.__mirrorAction === 'function') {
                window.__mirrorAction(action);
            }
        }
        
        // Capture clicks with coordinates
        document.addEventListener('click', function(e) {
            sendAction({
                type: 'click',
                x: e.clientX,
                y: e.clientY,
                pageX: e.pageX,
                pageY: e.pageY
            });
        }, true);
        
        // Capture mouse down/up for more precise clicking
        document.addEventListener('mousedown', function(e) {
            sendAction({
                type: 'mousedown',
                x: e.clientX,
                y: e.clientY,
                button: e.button
            });
        }, true);
        
        document.addEventListener('mouseup', function(e) {
            sendAction({
                type: 'mouseup',
                x: e.clientX,
                y: e.clientY,
                button: e.button
            });
        }, true);
        
        // Capture typing with keystrokes
        document.addEventListener('keydown', function(e) {
            // Skip modifier-only keys
            if (['Shift', 'Control', 'Alt', 'Meta'].includes(e.key)) return;
            
            sendAction({
                type: 'keydown',
                key: e.key,
                code: e.code
            });
        }, true);
        
        document.addEventListener('keyup', function(e) {
            if (['Shift', 'Control', 'Alt', 'Meta'].includes(e.key)) return;
            
            sendAction({
                type: 'keyup',
                key: e.key,
                code: e.code
            });
        }, true);
        
        // Capture scroll
        let scrollTimeout;
        window.addEventListener('scroll', function(e) {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(function() {
                sendAction({
                    type: 'scroll',
                    scrollX: window.scrollX,
                    scrollY: window.scrollY
                });
            }, 100);
        }, true);
        
        console.log('[Mirror] Action capture initialized!');
    })();
    """
    
    try:
        main_page.evaluate(capture_script)
        log_mirror_event('CAPTURE', 'Action capture script injected')
    except Exception as e:
        log_mirror_event('WARN', f'Script injection warning: {str(e)[:60]}')

def process_action_queue_direct(child_pages):
    """Process queued actions and mirror to child pages directly."""
    with mirror_lock:
        actions = mirror_state['action_queue'][:]
        mirror_state['action_queue'] = []
    
    for action in actions:
        action_type = action.get('type', '')
        start_time = time.time()
        
        for child_page in child_pages:
            try:
                if action_type == 'click':
                    x, y = action.get('x', 0), action.get('y', 0)
                    child_page.mouse.click(x, y)
                
                elif action_type == 'mousedown':
                    x, y = action.get('x', 0), action.get('y', 0)
                    child_page.mouse.move(x, y)
                    child_page.mouse.down()
                
                elif action_type == 'mouseup':
                    x, y = action.get('x', 0), action.get('y', 0)
                    child_page.mouse.move(x, y)
                    child_page.mouse.up()
                
                elif action_type == 'keydown':
                    key = action.get('key', '')
                    if key:
                        child_page.keyboard.down(key)
                
                elif action_type == 'keyup':
                    key = action.get('key', '')
                    if key:
                        child_page.keyboard.up(key)
                
                elif action_type == 'scroll':
                    x = action.get('scrollX', 0)
                    y = action.get('scrollY', 0)
                    child_page.evaluate(f'window.scrollTo({x}, {y})')
                
            except Exception as e:
                with mirror_lock:
                    mirror_state['metrics']['errors'] += 1
        
        latency = round((time.time() - start_time) * 1000)
        
        with mirror_lock:
            mirror_state['metrics']['actions_mirrored'] += 1
            mirror_state['metrics']['latencies'].append(latency)
        
        if action_type in ['click', 'keydown', 'scroll']:
            log_mirror_event('MIRROR', f'{action_type} mirrored to {len(child_pages)} children ({latency}ms)')

def cleanup_mirror_browsers():
    """Clean up all browser instances."""
    log_mirror_event('CLEANUP', 'Closing all browsers')
    
    with mirror_lock:
        for browser in mirror_state['browsers']:
            try:
                browser.close()
            except:
                pass
        
        if mirror_state['playwright']:
            try:
                mirror_state['playwright'].stop()
            except:
                pass
        
        mirror_state['browsers'] = []
        mirror_state['child_pages'] = []
        mirror_state['main_page'] = None
        mirror_state['playwright'] = None
        mirror_state['is_running'] = False
        mirror_state['stop_requested'] = False
    
    log_mirror_event('STOPPED', 'Mirror mode stopped')

@app.route('/api/mirror/start', methods=['POST'])
def start_mirror():
    """Start mirror mode with main + child browsers."""
    if mirror_state.get('is_running'):
        return jsonify({'error': 'Mirror mode already running'}), 400
    
    data = request.get_json() or {}
    
    config = {
        'url': data.get('url', ''),
        'num_children': min(int(data.get('num_children', 2)), 10),
        'headless_children': data.get('headless_children', True),
        'ignore_ssl': data.get('ignore_ssl', True)
    }
    
    if not config['url']:
        return jsonify({'error': 'URL is required'}), 400
    
    with mirror_lock:
        mirror_state['is_running'] = True
        mirror_state['stop_requested'] = False
        mirror_state['log'] = []
        mirror_state['action_queue'] = []
        mirror_state['config'] = config
        mirror_state['metrics'] = {
            'actions_mirrored': 0,
            'errors': 0,
            'latencies': []
        }
    
    # Start in background thread
    t = threading.Thread(target=start_mirror_browsers, args=(config,))
    t.start()
    
    return jsonify({
        'success': True,
        'message': f'Starting mirror mode: 1 main + {config["num_children"]} child browsers',
        'config': config
    })

@app.route('/api/mirror/stop', methods=['POST'])
def stop_mirror():
    """Stop mirror mode."""
    with mirror_lock:
        mirror_state['stop_requested'] = True
    
    log_mirror_event('STOP', 'Stop requested by user')
    
    return jsonify({
        'success': True,
        'message': 'Stopping mirror mode'
    })

@app.route('/api/mirror/action', methods=['POST'])
def receive_action():
    """Receive an action from the main browser to mirror."""
    data = request.get_json() or {}
    
    with mirror_lock:
        if mirror_state['is_running']:
            mirror_state['action_queue'].append(data)
    
    return jsonify({'success': True})

@app.route('/api/mirror/status')
def get_mirror_status():
    """Get current mirror mode status."""
    with mirror_lock:
        latencies = mirror_state['metrics']['latencies']
        avg_latency = round(sum(latencies) / len(latencies)) if latencies else 0
        
        return jsonify({
            'is_running': mirror_state['is_running'],
            'num_children': len(mirror_state['child_pages']),
            'children': [{'id': c['id'], 'status': c.get('status', 'unknown')} for c in mirror_state['child_pages']],
            'metrics': {
                'actions_mirrored': mirror_state['metrics']['actions_mirrored'],
                'errors': mirror_state['metrics']['errors'],
                'avg_latency': avg_latency
            },
            'log': mirror_state['log'][:50],
            'config': mirror_state['config']
        })


def apply_live_uuids_to_payload(payload: Any, live_uuids: Dict[str, Any]) -> Any:
    """
    Apply live UUIDs to the generated payload.
    
    Args:
        payload: The generated payload
        live_uuids: Dictionary containing live UUIDs from PC
        
    Returns:
        Modified payload with live UUIDs applied
    """
    if not isinstance(payload, dict) or not live_uuids:
        logger.info("No payload or live UUIDs provided, skipping UUID application")
        return payload
    
    logger.info(f"Applying live UUIDs to payload: {json.dumps(live_uuids, indent=2)}")
    
    # Make a deep copy to avoid modifying the original
    modified_payload = copy.deepcopy(payload)
    
    # Apply project reference if available
    if live_uuids.get('project', {}).get('uuid'):
        project_uuid = live_uuids['project']['uuid']
        if 'metadata' in modified_payload and 'project_reference' in modified_payload['metadata']:
            modified_payload['metadata']['project_reference']['uuid'] = project_uuid
    
    # Get resources section
    resources = modified_payload.get('spec', {}).get('resources', {})
    if not resources:
        return modified_payload
    
    # Handle runbook-specific resources
    runbook = resources.get('runbook', {})
    if runbook:
        # Apply live UUIDs to runbook tasks if needed
        for task in runbook.get('task_definition_list', []):
            # Apply cluster/environment references to runbook tasks if they have target references
            if live_uuids.get('cluster', {}).get('uuid') and 'target_any_local_reference' in task:
                if task['target_any_local_reference'].get('kind') == 'cluster':
                    task['target_any_local_reference']['uuid'] = live_uuids['cluster']['uuid']
    
    # Apply account references
    if live_uuids.get('account', {}).get('uuid'):
        # Use pc_uuid for payload generation if available, otherwise fall back to original uuid
        account_uuid = live_uuids['account'].get('pc_uuid')
        account_name = live_uuids['account'].get('name', '')
        original_uuid = live_uuids['account'].get('original_uuid', live_uuids['account']['uuid'])
        logger.info(f"Applying account UUID for payload: {account_uuid} (name: {account_name}, original: {original_uuid})")
        
        account_count = 0
        # Update substrate definitions - this is the main place where account_uuid is used
        for substrate in resources.get('substrate_definition_list', []):
            if 'create_spec' in substrate and 'resources' in substrate['create_spec']:
                substrate_resources = substrate['create_spec']['resources']
                old_uuid = substrate_resources.get('account_uuid', '')
                substrate_resources['account_uuid'] = account_uuid
                account_count += 1
                logger.info(f"Applied account to substrate create_spec {substrate.get('name', 'unnamed')}: UUID '{old_uuid}' -> '{account_uuid}'")
        
        # Update credential definitions if they reference accounts
        for cred in resources.get('credential_definition_list', []):
            if 'spec' in cred and 'resources' in cred['spec']:
                cred_resources = cred['spec']['resources']
                if 'account_reference' in cred_resources:
                    old_uuid = cred_resources['account_reference'].get('uuid', '')
                    cred_resources['account_reference']['uuid'] = account_uuid
                    logger.info(f"Applied account to credential {cred.get('name', 'unnamed')}: UUID '{old_uuid}' -> '{account_uuid}'")
        
        logger.info(f"Account UUID applied to {account_count} substrate locations")
    
    # Apply cluster references
    if live_uuids.get('cluster', {}).get('uuid'):
        cluster_uuid = live_uuids['cluster']['uuid']
        cluster_name = live_uuids['cluster'].get('name', '')
        logger.info(f"Applying cluster UUID: {cluster_uuid} (name: {cluster_name})")
        
        cluster_count = 0
        # Update substrate definitions
        for substrate in resources.get('substrate_definition_list', []):
            if 'spec' in substrate and 'resources' in substrate['spec']:
                substrate_resources = substrate['spec']['resources']
                if 'cluster_reference' in substrate_resources:
                    old_uuid = substrate_resources['cluster_reference'].get('uuid')
                    old_name = substrate_resources['cluster_reference'].get('name')
                    
                    substrate_resources['cluster_reference']['uuid'] = cluster_uuid
                    
                    # Update name if we have a valid cluster name
                    if cluster_name and cluster_name.strip() and cluster_name != cluster_uuid:
                        substrate_resources['cluster_reference']['name'] = cluster_name
                    else:
                        existing_name = substrate_resources['cluster_reference'].get('name', '')
                        # Check if existing name is empty, a UUID, or looks like a scaled index
                        if (not existing_name or 
                            existing_name == old_uuid or 
                            existing_name.isdigit() or 
                            existing_name == cluster_uuid):
                            substrate_resources['cluster_reference']['name'] = f"Cluster-{cluster_uuid[:8]}"
                    
                    cluster_count += 1
                    logger.info(f"Applied cluster to substrate {substrate.get('name', 'unnamed')}: UUID {old_uuid} -> {cluster_uuid}, Name: {substrate_resources['cluster_reference']['name']}")
            
            # Also check create_spec for cluster references
            if 'create_spec' in substrate:
                create_spec = substrate['create_spec']
                if 'cluster_reference' in create_spec:
                    old_uuid = create_spec['cluster_reference'].get('uuid')
                    old_name = create_spec['cluster_reference'].get('name')
                    
                    create_spec['cluster_reference']['uuid'] = cluster_uuid
                    
                    # Update name if we have a valid cluster name
                    if cluster_name and cluster_name.strip() and cluster_name != cluster_uuid:
                        create_spec['cluster_reference']['name'] = cluster_name
                    else:
                        existing_name = create_spec['cluster_reference'].get('name', '')
                        # Check if existing name is empty, a UUID, or looks like a scaled index
                        if (not existing_name or 
                            existing_name == old_uuid or 
                            existing_name.isdigit() or 
                            existing_name == cluster_uuid):
                            create_spec['cluster_reference']['name'] = f"Cluster-{cluster_uuid[:8]}"
                    
                    cluster_count += 1
                    logger.info(f"Applied cluster to substrate create_spec {substrate.get('name', 'unnamed')}: UUID {old_uuid} -> {cluster_uuid}, Name: {create_spec['cluster_reference']['name']}")
        
        logger.info(f"Cluster UUID applied to {cluster_count} locations")
    
    # Apply environment references
    if live_uuids.get('environment', {}).get('uuid'):
        env_uuid = live_uuids['environment']['uuid']
        env_name = live_uuids['environment'].get('name', '')
        logger.info(f"Applying environment UUID: {env_uuid} (name: {env_name})")
        
        # Update substrate definitions
        substrate_count = 0
        for substrate in resources.get('substrate_definition_list', []):
            if 'spec' in substrate and 'resources' in substrate['spec']:
                substrate_resources = substrate['spec']['resources']
                if 'environment_reference' in substrate_resources:
                    substrate_resources['environment_reference']['uuid'] = env_uuid
                    if env_name:
                        substrate_resources['environment_reference']['name'] = env_name
                    substrate_count += 1
                    logger.info(f"Applied environment UUID to substrate: {substrate.get('name', 'unnamed')}")
        
        # Also check if environment needs to be applied to the main payload metadata
        if 'metadata' in modified_payload:
            if 'project_reference' in modified_payload['metadata']:
                # Some payloads might have environment reference in metadata
                if 'environment_reference' in modified_payload['metadata']:
                    modified_payload['metadata']['environment_reference']['uuid'] = env_uuid
                    if env_name:
                        modified_payload['metadata']['environment_reference']['name'] = env_name
                    logger.info("Applied environment UUID to payload metadata")
        
        logger.info(f"Environment UUID applied to {substrate_count} substrates")
    
    # Apply network references
    if live_uuids.get('network', {}).get('uuid'):
        network_uuid = live_uuids['network']['uuid']
        network_name = live_uuids['network'].get('name', '')
        # Update substrate NICs
        for substrate in resources.get('substrate_definition_list', []):
            if 'spec' in substrate and 'resources' in substrate['spec']:
                substrate_resources = substrate['spec']['resources']
                for nic in substrate_resources.get('nic_list', []):
                    if 'subnet_reference' in nic:
                        nic['subnet_reference']['uuid'] = network_uuid
    
    # Apply subnet references
    if live_uuids.get('subnet', {}).get('uuid'):
        subnet_uuid = live_uuids['subnet']['uuid']
        subnet_name = live_uuids['subnet'].get('name', '')
        # Update substrate NICs (if different from network)
        for substrate in resources.get('substrate_definition_list', []):
            if 'spec' in substrate and 'resources' in substrate['spec']:
                substrate_resources = substrate['spec']['resources']
                for nic in substrate_resources.get('nic_list', []):
                    if 'subnet_reference' in nic and not live_uuids.get('network', {}).get('uuid'):
                        nic['subnet_reference']['uuid'] = subnet_uuid
                        if subnet_name:
                            nic['subnet_reference']['name'] = subnet_name
    
    # Apply image references
    if live_uuids.get('image', {}).get('uuid'):
        image_uuid = live_uuids['image']['uuid']
        image_name = live_uuids['image'].get('name', '')
        # Update substrate resources
        for substrate in resources.get('substrate_definition_list', []):
            if 'spec' in substrate and 'resources' in substrate['spec']:
                substrate_resources = substrate['spec']['resources']
                for disk in substrate_resources.get('disk_list', []):
                    if 'data_source_reference' in disk:
                        disk['data_source_reference']['uuid'] = image_uuid
                        if image_name:
                            disk['data_source_reference']['name'] = image_name
    
    # Apply comprehensive UUID mappings for all entity types
    apply_comprehensive_uuid_mappings(modified_payload, live_uuids)
    
    return modified_payload


def apply_comprehensive_uuid_mappings(payload: Dict[str, Any], live_uuids: Dict[str, Any]) -> None:
    """
    Apply comprehensive UUID mappings for all entity types in the payload.
    This handles cross-entity references like package_definition_list and service_definition_list.
    """
    if not isinstance(payload, dict):
        return
    
    logger.info("Applying comprehensive UUID mappings for all entity types")
    
    # Extract UUIDs from all definition lists
    app_package_definition_uuids = []
    app_service_definition_uuids = []
    app_substrate_definition_uuids = []
    app_credential_definition_uuids = []
    app_profile_deployment_uuids = []
    
    # Get resources section
    resources = payload.get('spec', {}).get('resources', {})
    
    # Extract package definition UUIDs
    for package_def in resources.get('package_definition_list', []):
        if 'uuid' in package_def:
            app_package_definition_uuids.append(package_def['uuid'])
            logger.info(f"Found package_definition UUID: {package_def['uuid']} (name: {package_def.get('name', 'unnamed')})")
    
    # Extract service definition UUIDs  
    for service_def in resources.get('service_definition_list', []):
        if 'uuid' in service_def:
            app_service_definition_uuids.append(service_def['uuid'])
            logger.info(f"Found service_definition UUID: {service_def['uuid']} (name: {service_def.get('name', 'unnamed')})")
    
    # Extract substrate definition UUIDs
    for substrate_def in resources.get('substrate_definition_list', []):
        if 'uuid' in substrate_def:
            app_substrate_definition_uuids.append(substrate_def['uuid'])
            logger.info(f"Found substrate_definition UUID: {substrate_def['uuid']} (name: {substrate_def.get('name', 'unnamed')})")
    
    # Extract credential definition UUIDs
    for credential_def in resources.get('credential_definition_list', []):
        if 'uuid' in credential_def:
            app_credential_definition_uuids.append(credential_def['uuid'])
            logger.info(f"Found credential_definition UUID: {credential_def['uuid']} (name: {credential_def.get('name', 'unnamed')})")
    
    # Extract deployment UUIDs from app_profile_list
    for app_profile in resources.get('app_profile_list', []):
        for deployment in app_profile.get('deployment_create_list', []):
            if 'uuid' in deployment:
                app_profile_deployment_uuids.append(deployment['uuid'])
                logger.info(f"Found deployment UUID: {deployment['uuid']} (name: {deployment.get('name', 'unnamed')})")
    
    logger.info(f"Found {len(app_package_definition_uuids)} package definition UUIDs: {app_package_definition_uuids}")
    logger.info(f"Found {len(app_service_definition_uuids)} service definition UUIDs: {app_service_definition_uuids}")
    logger.info(f"Found {len(app_substrate_definition_uuids)} substrate definition UUIDs: {app_substrate_definition_uuids}")
    logger.info(f"Found {len(app_credential_definition_uuids)} credential definition UUIDs: {app_credential_definition_uuids}")
    logger.info(f"Found {len(app_profile_deployment_uuids)} deployment UUIDs: {app_profile_deployment_uuids}")
    
    # Apply UUID mappings throughout the payload
    def apply_uuid_mappings_recursive(obj):
        """Recursively apply UUID mappings to all references"""
        if isinstance(obj, dict):
            # Handle target_any_local_reference for app_package
            if ('target_any_local_reference' in obj and 
                isinstance(obj['target_any_local_reference'], dict) and 
                obj['target_any_local_reference'].get('kind') == 'app_package'):
                
                # Use the first package definition UUID if available
                if app_package_definition_uuids:
                    old_uuid = obj['target_any_local_reference'].get('uuid')
                    obj['target_any_local_reference']['uuid'] = app_package_definition_uuids[0]
                    logger.info(f"Updated target_any_local_reference (app_package) UUID: {old_uuid} -> {app_package_definition_uuids[0]}")
            
            # Handle target_any_local_reference for app_service
            if ('target_any_local_reference' in obj and 
                isinstance(obj['target_any_local_reference'], dict) and 
                obj['target_any_local_reference'].get('kind') == 'app_service'):
                
                # Use the first service definition UUID if available
                if app_service_definition_uuids:
                    old_uuid = obj['target_any_local_reference'].get('uuid')
                    obj['target_any_local_reference']['uuid'] = app_service_definition_uuids[0]
                    logger.info(f"Updated target_any_local_reference (app_service) UUID: {old_uuid} -> {app_service_definition_uuids[0]}")
            
            # Handle package_local_reference_list
            if 'package_local_reference_list' in obj and isinstance(obj['package_local_reference_list'], list):
                for i, package_ref in enumerate(obj['package_local_reference_list']):
                    if isinstance(package_ref, dict) and package_ref.get('kind') == 'app_package':
                        if i < len(app_package_definition_uuids):
                            old_uuid = package_ref.get('uuid')
                            package_ref['uuid'] = app_package_definition_uuids[i]
                            logger.info(f"Updated package_local_reference_list[{i}] UUID: {old_uuid} -> {app_package_definition_uuids[i]}")
            
            # Handle service_local_reference_list
            if 'service_local_reference_list' in obj and isinstance(obj['service_local_reference_list'], list):
                for i, service_ref in enumerate(obj['service_local_reference_list']):
                    if isinstance(service_ref, dict) and service_ref.get('kind') == 'app_service':
                        if i < len(app_service_definition_uuids):
                            old_uuid = service_ref.get('uuid')
                            service_ref['uuid'] = app_service_definition_uuids[i]
                            logger.info(f"Updated service_local_reference_list[{i}] UUID: {old_uuid} -> {app_service_definition_uuids[i]}")
            
            # Handle any other app_package references
            if obj.get('kind') == 'app_package' and 'uuid' in obj and app_package_definition_uuids:
                # Only update if this is a reference (not the definition itself)
                if obj['uuid'] not in app_package_definition_uuids:
                    old_uuid = obj['uuid']
                    obj['uuid'] = app_package_definition_uuids[0]
                    logger.info(f"Updated app_package reference UUID: {old_uuid} -> {app_package_definition_uuids[0]}")
            
            # Handle any other app_service references
            if obj.get('kind') == 'app_service' and 'uuid' in obj and app_service_definition_uuids:
                # Only update if this is a reference (not the definition itself)
                if obj['uuid'] not in app_service_definition_uuids:
                    old_uuid = obj['uuid']
                    obj['uuid'] = app_service_definition_uuids[0]
                    logger.info(f"Updated app_service reference UUID: {old_uuid} -> {app_service_definition_uuids[0]}")
            
            # Handle substrate_local_reference for app_substrate
            if ('substrate_local_reference' in obj and 
                isinstance(obj['substrate_local_reference'], dict) and 
                obj['substrate_local_reference'].get('kind') == 'app_substrate'):
                
                # Use the first substrate definition UUID if available
                if app_substrate_definition_uuids:
                    old_uuid = obj['substrate_local_reference'].get('uuid')
                    obj['substrate_local_reference']['uuid'] = app_substrate_definition_uuids[0]
                    logger.info(f"Updated substrate_local_reference UUID: {old_uuid} -> {app_substrate_definition_uuids[0]}")
            
            # Handle any other app_substrate references
            if obj.get('kind') == 'app_substrate' and 'uuid' in obj and app_substrate_definition_uuids:
                # Only update if this is a reference (not the definition itself)
                if obj['uuid'] not in app_substrate_definition_uuids:
                    old_uuid = obj['uuid']
                    obj['uuid'] = app_substrate_definition_uuids[0]
                    logger.info(f"Updated app_substrate reference UUID: {old_uuid} -> {app_substrate_definition_uuids[0]}")
            
            # Handle default_credential_local_reference
            if ('default_credential_local_reference' in obj and 
                isinstance(obj['default_credential_local_reference'], dict) and 
                obj['default_credential_local_reference'].get('kind') == 'app_credential'):
                
                # Use the first credential definition UUID if available
                if app_credential_definition_uuids:
                    old_uuid = obj['default_credential_local_reference'].get('uuid')
                    obj['default_credential_local_reference']['uuid'] = app_credential_definition_uuids[0]
                    logger.info(f"Updated default_credential_local_reference UUID: {old_uuid} -> {app_credential_definition_uuids[0]}")
            
            # Handle login_credential_local_reference
            if ('login_credential_local_reference' in obj and 
                isinstance(obj['login_credential_local_reference'], dict) and 
                obj['login_credential_local_reference'].get('kind') == 'app_credential'):
                
                # Use the first credential definition UUID if available
                if app_credential_definition_uuids:
                    old_uuid = obj['login_credential_local_reference'].get('uuid')
                    obj['login_credential_local_reference']['uuid'] = app_credential_definition_uuids[0]
                    logger.info(f"Updated login_credential_local_reference UUID: {old_uuid} -> {app_credential_definition_uuids[0]}")
            
            # Handle any other app_credential references
            if obj.get('kind') == 'app_credential' and 'uuid' in obj and app_credential_definition_uuids:
                # Only update if this is a reference (not the definition itself)
                if obj['uuid'] not in app_credential_definition_uuids:
                    old_uuid = obj['uuid']
                    obj['uuid'] = app_credential_definition_uuids[0]
                    logger.info(f"Updated app_credential reference UUID: {old_uuid} -> {app_credential_definition_uuids[0]}")
            
            # Handle client_attrs - map deployment UUIDs as keys
            if 'client_attrs' in obj and isinstance(obj['client_attrs'], dict) and app_profile_deployment_uuids:
                # Get current client_attrs keys
                current_keys = list(obj['client_attrs'].keys())
                if current_keys and app_profile_deployment_uuids:
                    # Map each deployment UUID to client_attrs
                    new_client_attrs = {}
                    for i, deployment_uuid in enumerate(app_profile_deployment_uuids):
                        if i < len(current_keys):
                            # Use the existing value but with the new deployment UUID as key
                            new_client_attrs[deployment_uuid] = obj['client_attrs'][current_keys[i]]
                            logger.info(f"Updated client_attrs key: {current_keys[i]} -> {deployment_uuid}")
                        else:
                            # If we have more deployments than client_attrs, create new entries
                            new_client_attrs[deployment_uuid] = {"x": 100 + i * 50, "y": 100 + i * 50}
                            logger.info(f"Added new client_attrs entry for deployment: {deployment_uuid}")
                    
                    obj['client_attrs'] = new_client_attrs
            
            # Handle cluster_reference specifically
            if 'cluster_reference' in obj and live_uuids.get('cluster', {}).get('uuid'):
                cluster_uuid = live_uuids['cluster']['uuid']
                cluster_name = live_uuids['cluster'].get('name', '')
                old_uuid = obj['cluster_reference'].get('uuid')
                old_name = obj['cluster_reference'].get('name')
                
                # Always update UUID
                obj['cluster_reference']['uuid'] = cluster_uuid
                
                # Update name if we have a valid cluster name, otherwise keep existing or use UUID
                if cluster_name and cluster_name.strip() and cluster_name != cluster_uuid:
                    obj['cluster_reference']['name'] = cluster_name
                    logger.info(f"Updated cluster_reference: UUID {old_uuid} -> {cluster_uuid}, Name: {old_name} -> {cluster_name}")
                else:
                    # If no valid name provided, keep existing name or use a fallback
                    existing_name = obj['cluster_reference'].get('name', '')
                    # Check if existing name is empty, a UUID, or looks like a scaled index (just numbers)
                    if (not existing_name or 
                        existing_name == old_uuid or 
                        existing_name.isdigit() or 
                        existing_name == cluster_uuid):
                        obj['cluster_reference']['name'] = f"Cluster-{cluster_uuid[:8]}"
                        logger.info(f"Updated cluster_reference UUID: {old_uuid} -> {cluster_uuid}, Name: {existing_name} -> Cluster-{cluster_uuid[:8]}")
                    else:
                        logger.info(f"Updated cluster_reference UUID: {old_uuid} -> {cluster_uuid}, Name unchanged: {existing_name}")
            
            # Handle environment_reference specifically
            if 'environment_reference' in obj and live_uuids.get('environment', {}).get('uuid'):
                env_uuid = live_uuids['environment']['uuid']
                env_name = live_uuids['environment'].get('name', '')
                old_uuid = obj['environment_reference'].get('uuid')
                obj['environment_reference']['uuid'] = env_uuid
                if env_name:
                    obj['environment_reference']['name'] = env_name
                logger.info(f"Updated environment_reference UUID: {old_uuid} -> {env_uuid}")
            
            # Handle account_reference specifically
            if 'account_reference' in obj and live_uuids.get('account', {}).get('uuid'):
                # Use pc_uuid for account references if available, otherwise fall back to original uuid
                account_uuid = live_uuids['account'].get('pc_uuid') or live_uuids['account']['uuid']
                account_name = live_uuids['account'].get('name', '')
                old_uuid = obj['account_reference'].get('uuid')
                obj['account_reference']['uuid'] = account_uuid
                if account_name:
                    obj['account_reference']['name'] = account_name
                logger.info(f"Updated account_reference UUID: {old_uuid} -> {account_uuid} (using {'pc_uuid' if live_uuids['account'].get('pc_uuid') else 'original_uuid'})")
            
            # Handle network/subnet references
            if 'subnet_reference' in obj:
                if live_uuids.get('subnet', {}).get('uuid'):
                    subnet_uuid = live_uuids['subnet']['uuid']
                    subnet_name = live_uuids['subnet'].get('name', '')
                    old_uuid = obj['subnet_reference'].get('uuid')
                    obj['subnet_reference']['uuid'] = subnet_uuid
                    if subnet_name:
                        obj['subnet_reference']['name'] = subnet_name
                    logger.info(f"Updated subnet_reference UUID: {old_uuid} -> {subnet_uuid}")
                elif live_uuids.get('network', {}).get('uuid'):
                    network_uuid = live_uuids['network']['uuid']
                    network_name = live_uuids['network'].get('name', '')
                    old_uuid = obj['subnet_reference'].get('uuid')
                    obj['subnet_reference']['uuid'] = network_uuid
                    if network_name:
                        obj['subnet_reference']['name'] = network_name
                    logger.info(f"Updated subnet_reference UUID (from network): {old_uuid} -> {network_uuid}")
            
            # Handle image/data_source references
            if 'data_source_reference' in obj and live_uuids.get('image', {}).get('uuid'):
                image_uuid = live_uuids['image']['uuid']
                image_name = live_uuids['image'].get('name', '')
                old_uuid = obj['data_source_reference'].get('uuid')
                obj['data_source_reference']['uuid'] = image_uuid
                if image_name:
                    obj['data_source_reference']['name'] = image_name
                logger.info(f"Updated data_source_reference UUID: {old_uuid} -> {image_uuid}")
            
            # Recursively process nested objects
            for value in obj.values():
                apply_uuid_mappings_recursive(value)
                
        elif isinstance(obj, list):
            for item in obj:
                apply_uuid_mappings_recursive(item)
    
    # Apply mappings to the entire payload
    apply_uuid_mappings_recursive(payload)
    logger.info("Comprehensive UUID mapping completed")


# ============================================================================
# LIVE UUID API ENDPOINTS
# ============================================================================

# API Domain Suffix Mapping
API_DOMAIN_SUFFIXES = {
    'dm': ['projects', 'projects/list'],
    'iam': ['users'],
    'services': ['blueprint', 'groups', 'v1/groups'],
    'ncm': ['api/nutanix/v3/nutanix/v1/groups/list']
}

def build_api_url(pc_url, service_type, endpoint):
    """
    Build API URL based on PC URL and service type.
    
    Args:
        pc_url: Base PC URL (e.g., https://iam.nconprem-10-53-58-35.ccpnx.com/ or https://10.53.60.176:9440/)
        service_type: Type of service (dm, iam, services, ncm)
        endpoint: API endpoint path
    
    Returns:
        Complete API URL
    """
    # Clean up PC URL
    pc_url = pc_url.rstrip('/')
    
    # Extract domain from PC URL
    if '://' in pc_url:
        protocol, domain_part = pc_url.split('://', 1)
    else:
        protocol = 'https'
        domain_part = pc_url
    
    # Remove port if present for IP detection
    domain_without_port = domain_part.split(':')[0]
    
    # Check if it's an IP address
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    is_ip_address = re.match(ip_pattern, domain_without_port)
    
    if is_ip_address:
        # For IP addresses, use the original URL without service suffixes
        logger.info(f"Detected IP address in PC URL: {domain_part}, using original URL without suffixes")
        service_url = pc_url
    else:
        # Extract base domain (remove subdomain if present)
        if domain_part.count('.') >= 2:
            # Has subdomain like iam.nconprem-10-53-58-35.ccpnx.com
            parts = domain_part.split('.', 1)
            base_domain = parts[1]  # nconprem-10-53-58-35.ccpnx.com
        else:
            # Simple domain
            base_domain = domain_part
        
        # Build service-specific URL for domain names
        if service_type == 'dm':
            service_url = f"{protocol}://dm.services.{base_domain}"
        elif service_type == 'iam':
            service_url = f"{protocol}://iam.{base_domain}"
        elif service_type == 'services':
            service_url = f"{protocol}://services.{base_domain}"
        elif service_type == 'ncm':
            service_url = f"{protocol}://ncm.services.{base_domain}"
        else:
            # Default to original URL
            service_url = pc_url
    
    # Combine with endpoint
    final_url = f"{service_url}/{endpoint}"
    logger.info(f"Built API URL: {final_url} (service_type: {service_type})")
    return final_url

@app.route('/api/live-uuid/projects', methods=['POST'])
def get_projects():
    """Get project list from live PC."""
    try:
        data = request.get_json()
        pc_url = data.get('pc_url', '')
        search_term = data.get('search_term', '')
        username = data.get('username', 'admin')
        password = data.get('password', 'Nutanix.123')
        
        logger.info(f"Fetching projects from PC: {pc_url} with user: {username}")
        
        if not pc_url:
            logger.error("PC URL is required")
            return jsonify({'error': 'PC URL is required'}), 400
        
        # Build API URL
        api_url = build_api_url(pc_url, 'dm', 'api/nutanix/v3/projects/list')
        
        # Build payload
        payload = {
            "length": 20,
            "offset": 0,
            "kind": "project"
        }
        
        # Add search filter if provided
        if search_term:
            # Create case-insensitive regex filter
            filter_pattern = '.*'.join([f'[{c.lower()}|{c.upper()}]' for c in search_term])
            payload["filter"] = f"name==.*{filter_pattern}.*"
        
        # Create authenticated session
        session = requests.Session()
        session.auth = HTTPBasicAuth(username, password)
        session.headers = {'Content-Type': 'application/json'}
        session.verify = False
        
        logger.info(f"Making API call to: {api_url}")
        logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
        
        # Make API call
        response = session.post(
            api_url,
            json=payload,
            timeout=30
        )
        
        logger.info(f"API response status: {response.status_code}")
        
        if response.status_code == 200:
            projects_data = response.json()
            logger.info(f"Successfully fetched {len(projects_data.get('entities', []))} projects")
            
            # Extract simplified project list
            projects = []
            for entity in projects_data.get('entities', []):
                project = {
                    'uuid': entity.get('metadata', {}).get('uuid'),
                    'name': entity.get('spec', {}).get('name'),
                    'resources': entity.get('spec', {}).get('resources', {})
                }
                projects.append(project)
                logger.debug(f"Project: {project['name']} ({project['uuid']})")
            
            response_data = {
                'success': True,
                'projects': projects,
                'total_matches': projects_data.get('metadata', {}).get('total_matches', 0)
            }
            
            # Log PC API request/response
            log_api_request_response(
                api_name="pc_projects",
                endpoint=api_url,
                method="POST",
                request_data={
                    'pc_url': pc_url,
                    'search_term': search_term,
                    'username': username,
                    'payload': payload
                },
                response_data=response_data,
                status_code=200
            )
            
            return jsonify(response_data)
        else:
            logger.error(f"API call failed with status {response.status_code}: {response.text}")
            error_response = {
                'error': f'API call failed with status {response.status_code}',
                'details': response.text
            }
            
            # Log PC API error
            log_api_request_response(
                api_name="pc_projects",
                endpoint=api_url,
                method="POST",
                request_data={
                    'pc_url': pc_url,
                    'search_term': search_term,
                    'username': username,
                    'payload': payload
                },
                response_data=error_response,
                status_code=response.status_code,
                error=response.text
            )
            
            return jsonify(error_response), response.status_code
            
    except Exception as e:
        logger.error(f"Exception in get_projects: {str(e)}", exc_info=True)
        error_response = {'error': str(e)}
        
        # Log PC API exception
        log_api_request_response(
            api_name="pc_projects",
            endpoint="/api/live-uuid/projects",
            method="POST",
            request_data=request.json,
            response_data=error_response,
            status_code=500,
            error=str(e)
        )
        
        return jsonify(error_response), 500

@app.route('/api/live-uuid/images', methods=['POST'])
def get_images():
    """Get images list from live PC."""
    try:
        data = request.get_json()
        print(f"Data: {data}")
        pc_url = data.get('pc_url', '')
        account_uuid = data.get('account_uuid', '')
        project_uuid = data.get('project_uuid', '')
        username = data.get('username', 'admin')
        password = data.get('password', 'Nutanix.123')
        use_sample_data = data.get('use_sample_data', False)  # Test mode flag
        
        logger.info(f"Fetching images from PC: {pc_url} for account: {account_uuid}")
        
        if not pc_url:
            logger.error("PC URL is required")
            return jsonify({'error': 'PC URL is required'}), 400
        if not account_uuid:
            logger.error("Account UUID is required")
            return jsonify({'error': 'Account UUID is required'}), 400
        
        # Build API URL
        api_url = build_api_url(pc_url, 'ncm', 'api/nutanix/v3/nutanix/v1/groups/list')
        
        # Build payload
        payload = {
            "entity_type": "image_info",
            "query_name": "test",
            "group_member_attributes": [
                {"attribute": "uuid"},
                {"attribute": "name"},
                {"attribute": "image_type"},
                {"attribute": "vmdisk_size"}
            ],
            "filter_criteria": f"account_uuid=={account_uuid}"
        }
        
        logger.info(f"Image Payload immediately after construction: {payload}")
        logger.info(f"Account UUID used in filter: {account_uuid}")
        

        
        logger.info(f"Image Payload before session: {payload}")
        # Create authenticated session
        session = requests.Session()
        session.auth = HTTPBasicAuth(username, password)
        session.headers = {'Content-Type': 'application/json'}
        session.verify = False
        
        logger.info(f"Making images API call to: {api_url}")
        logger.info(f"Image Payload after session: {payload}")
        logger.info(f"Images payload (formatted): {json.dumps(payload, indent=2)}")
        
        # Make API call
        logger.info(f"About to send POST request to: {api_url}")
        logger.info(f"Request payload type: {type(payload)}")
        logger.info(f"Request payload content: {payload}")
        logger.info(f"Request payload JSON serialized: {json.dumps(payload)}")
        logger.info(f"Session headers: {session.headers}")
        logger.info(f"Session auth: {session.auth}")
        
        response = session.post(
            api_url,
            json=payload,
            timeout=30
        )
        
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        logger.info(f"Images API response status: {response.status_code}")
        
        if response.status_code == 200:
            images_data = response.json()
            
            # Extract simplified images list
            images = []
            
            # Handle both old format (group_results) and new format (direct entity list)
            entities_to_process = []
            
            if 'group_results' in images_data:
                # Old format: group_results -> entity_results
                for group in images_data.get('group_results', []):
                    for entity in group.get('entity_results', []):
                        entities_to_process.append(entity)
            else:
                # New format: direct entity list or entities array
                entities_to_process = images_data.get('entities', images_data.get('entity_results', []))
            
            for entity in entities_to_process:
                # Initialize variables for each entity
                name = None
                image_type = None
                vmdisk_size = None
                
                # Handle new format where entity_id is the image UUID
                if 'entity_id' in entity:
                    try:
                        for data in entity.get('data', []):
                            if data['name'] == 'name':
                                name = data['values'][0]['values'][0]
                            elif data['name'] == 'image_type':
                                image_type = data['values'][0]['values'][0]
                            elif data['name'] == 'vmdisk_size':
                                vmdisk_size = data['values'][0]['values'][0]
                    except Exception as e:
                        logger.error(f"Error processing entity: {str(e)}", exc_info=True)
                        continue
                    if not name or not image_type or not vmdisk_size:
                        logger.error(f"Missing required fields for entity: {entity.get('entity_id', '')}")
                        continue
                    # New format with entity_id as UUID
                    image = {
                        'uuid': entity.get('entity_id', ''),
                        'name': name,
                        'image_type': image_type,
                        'vmdisk_size': vmdisk_size
                    }
                    images.append(image)
                    logger.debug(f"Image: {image['name']} ({image['uuid']})")
            
            logger.info(f"Successfully fetched {len(images)} images")
            response_data = {
                'success': True,
                'images': images,
                'total_matches': len(images)
            }
            
            # Log PC API request/response
            log_api_request_response(
                api_name="pc_images",
                endpoint=api_url,
                method="POST",
                request_data={
                    'pc_url': pc_url,
                    'account_uuid': account_uuid,
                    'project_uuid': project_uuid,
                    'username': username,
                    'payload': payload
                },
                response_data=response_data,
                status_code=200
            )
            
            return jsonify(response_data)
        else:
            logger.error(f"Images API call failed with status {response.status_code}: {response.text}")
            error_response = {
                'error': f'API call failed with status {response.status_code}',
                'details': response.text
            }
            
            # Log PC API error
            log_api_request_response(
                api_name="pc_images",
                endpoint=api_url,
                method="POST",
                request_data={
                    'pc_url': pc_url,
                    'account_uuid': account_uuid,
                    'project_uuid': project_uuid,
                    'username': username,
                    'payload': payload
                },
                response_data=error_response,
                status_code=response.status_code,
                error=response.text
            )
            
            return jsonify(error_response), response.status_code
            
    except Exception as e:
        error_response = {'error': str(e)}
        
        # Log PC API exception
        log_api_request_response(
            api_name="pc_images",
            endpoint="/api/live-uuid/images",
            method="POST",
            request_data=request.json,
            response_data=error_response,
            status_code=500,
            error=str(e)
        )
        
        return jsonify(error_response), 500

@app.route('/api/live-uuid/account-details', methods=['POST'])
def get_account_details():
    """
    Fetch account details for given account UUIDs using GET API calls.
    Returns account details including pc_uuid which should be used as the actual account UUID.
    """
    try:
        data = request.get_json()
        pc_url = data.get('pc_url', '').strip()
        username = data.get('username', 'admin')
        password = data.get('password', 'Nutanix.123')
        account_uuids = data.get('account_uuids', [])
        
        if not pc_url or not account_uuids:
            return jsonify({
                'success': False,
                'error': 'PC URL and account UUIDs are required'
            })
        
        logger.info(f"Fetching details for {len(account_uuids)} accounts from PC: {pc_url}")
        
        accounts = []
        for account_uuid in account_uuids:
            try:
                # Build the account details API URL
                account_api_url = build_api_url(pc_url, 'services', f'/api/nutanix/v3/accounts/{account_uuid}')
                logger.info(f"Fetching account details from: {account_api_url}")
                
                response = requests.get(
                    account_api_url,
                    auth=HTTPBasicAuth(username, password),
                    headers={'Content-Type': 'application/json'},
                    verify=False,
                    timeout=30
                )
                
                if response.status_code == 200:
                    account_data = response.json()
                    
                    # Extract account details
                    account_name = account_data.get('spec', {}).get('name', f'Account-{account_uuid[:8]}')
                    pc_uuid_list = account_data.get('spec', {}).get('resources', {}).get('data', {}).get('cluster_account_reference_list', [])
                    try:
                        pc_uuid = pc_uuid_list[0]
                    except Exception as e:
                        logger.error(f"Error fetching PC UUID for account {account_uuid}: {str(e)}")
                        return jsonify({
                            'success': False,
                            'error': str(e)
                        })
                    accounts.append({
                        'uuid': account_uuid,
                        'name': account_name,
                        'pc_uuid': pc_uuid,
                        'status': 'SUCCESS'
                    })
                    
                    logger.info(f"Successfully fetched account: {account_name} (UUID: {account_uuid}, PC_UUID: {pc_uuid})")
                    
                else:
                    logger.warning(f"Failed to fetch account {account_uuid}: HTTP {response.status_code}")
                    accounts.append({
                        'uuid': account_uuid,
                        'name': f'Account-{account_uuid[:8]}',
                        'pc_uuid': account_uuid,
                        'status': f'HTTP_{response.status_code}'
                    })
                    
            except Exception as e:
                logger.error(f"Error fetching account {account_uuid}: {str(e)}")
                accounts.append({
                    'uuid': account_uuid,
                    'name': f'Account-{account_uuid[:8]}',
                    'pc_uuid': account_uuid,
                    'status': 'ERROR'
                })
        
        return jsonify({
            'success': True,
            'accounts': accounts
        })
        
    except Exception as e:
        logger.error(f"Error in get_account_details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/live-uuid/cluster-names', methods=['POST'])
def get_cluster_names():
    """
    Fetch cluster names for given cluster UUIDs using GET API calls.
    
    Expected payload:
    {
        "pc_url": "https://10.115.150.123:9440/",
        "username": "admin",
        "password": "password",
        "cluster_uuids": ["uuid1", "uuid2", ...]
    }
    """
    try:
        data = request.get_json()
        pc_url = data.get('pc_url')
        username = data.get('username')
        password = data.get('password')
        cluster_uuids = data.get('cluster_uuids', [])
        
        if not pc_url or not username or not password:
            return jsonify({'error': 'PC URL, username, and password are required'}), 400
        
        if not cluster_uuids:
            return jsonify({'error': 'Cluster UUIDs are required'}), 400
        
        logger.info(f"Fetching cluster names for {len(cluster_uuids)} clusters from PC: {pc_url}")
        
        # Create authenticated session
        session = requests.Session()
        session.auth = HTTPBasicAuth(username, password)
        session.headers = {'Content-Type': 'application/json'}
        session.verify = False
        
        cluster_names = []
        
        for cluster_uuid in cluster_uuids:
            try:
                # Build cluster GET API URL
                cluster_api_url = f"{pc_url.rstrip('/')}/api/nutanix/v3/clusters/{cluster_uuid}"
                logger.info(f"Fetching cluster details from: {cluster_api_url}")
                
                response = session.get(cluster_api_url, timeout=30)
                
                if response.status_code == 200:
                    cluster_data = response.json()
                    cluster_name = cluster_data.get('spec', {}).get('name', f'Cluster-{cluster_uuid[:8]}')
                    
                    cluster_names.append({
                        'uuid': cluster_uuid,
                        'name': cluster_name,
                        'status': cluster_data.get('status', {}).get('state', 'UNKNOWN')
                    })
                    
                    logger.info(f"Successfully fetched cluster: {cluster_name} ({cluster_uuid})")
                else:
                    logger.warning(f"Failed to fetch cluster {cluster_uuid}: HTTP {response.status_code}")
                    cluster_names.append({
                        'uuid': cluster_uuid,
                        'name': f'Cluster-{cluster_uuid[:8]} (Error)',
                        'status': 'ERROR'
                    })
                    
            except Exception as e:
                logger.error(f"Error fetching cluster {cluster_uuid}: {str(e)}")
                cluster_names.append({
                    'uuid': cluster_uuid,
                    'name': f'Cluster-{cluster_uuid[:8]} (Error)',
                    'status': 'ERROR'
                })
        
        logger.info(f"Successfully fetched names for {len(cluster_names)} clusters")
        
        return jsonify({
            'success': True,
            'clusters': cluster_names
        })
        
    except Exception as e:
        logger.error(f"Error in get_cluster_names: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/live-uuid/test-connection', methods=['POST'])
def test_pc_connection():
    """Test connection to PC."""
    try:
        data = request.get_json()
        pc_url = data.get('pc_url', '')
        username = data.get('username', 'admin')
        password = data.get('password', 'Nutanix.123')
        
        logger.info(f"Testing connection to PC: {pc_url} with user: {username}")
        
        if not pc_url:
            logger.error("PC URL is required for connection test")
            return jsonify({'error': 'PC URL is required'}), 400
        
        # Try to connect to a simple endpoint
        test_url = build_api_url(pc_url, 'dm', 'api/nutanix/v3/projects/list')
        
        # Create authenticated session
        session = requests.Session()
        session.auth = HTTPBasicAuth(username, password)
        session.headers = {'Content-Type': 'application/json'}
        session.verify = False
        
        logger.info(f"Testing connection to: {test_url}")
        
        response = session.post(
            test_url,
            json={"length": 1, "offset": 0, "kind": "project"},
            timeout=10
        )
        
        logger.info(f"Connection test response status: {response.status_code}")
        
        if response.status_code == 200:
            logger.info("Connection test successful")
            response_data = {
                'success': True,
                'message': 'Connection successful',
                'status_code': response.status_code
            }
            
            # Log PC API request/response
            log_api_request_response(
                api_name="pc_test_connection",
                endpoint=test_url,
                method="POST",
                request_data={
                    'pc_url': pc_url,
                    'username': username,
                    'test_payload': {"length": 1, "offset": 0, "kind": "project"}
                },
                response_data=response_data,
                status_code=200
            )
            
            return jsonify(response_data)
        else:
            logger.warning(f"Connection test failed with status {response.status_code}")
            error_response = {
                'success': False,
                'message': f'Connection failed with status {response.status_code}',
                'status_code': response.status_code
            }
            
            # Log PC API error
            log_api_request_response(
                api_name="pc_test_connection",
                endpoint=test_url,
                method="POST",
                request_data={
                    'pc_url': pc_url,
                    'username': username,
                    'test_payload': {"length": 1, "offset": 0, "kind": "project"}
                },
                response_data=error_response,
                status_code=response.status_code,
                error=f"Connection test failed with status {response.status_code}"
            )
            
            return jsonify(error_response)
            
    except Exception as e:
        error_response = {
            'success': False,
            'error': str(e)
        }
        
        # Log PC API exception
        log_api_request_response(
            api_name="pc_test_connection",
            endpoint="/api/live-uuid/test-connection",
            method="POST",
            request_data=request.json,
            response_data=error_response,
            status_code=500,
            error=str(e)
        )
        
        return jsonify(error_response), 500

@app.route('/api/log-frontend', methods=['POST'])
def log_frontend():
    """Receive logs from frontend JavaScript"""
    try:
        data = request.get_json()
        level = data.get('level', 'INFO')
        message = data.get('message', '')
        log_data = data.get('data', {})
        
        # Log to backend with frontend prefix
        if level == 'ERROR':
            logger.error(f"FRONTEND: {message} - Data: {log_data}")
        elif level == 'WARNING':
            logger.warning(f"FRONTEND: {message} - Data: {log_data}")
        else:
            logger.info(f"FRONTEND: {message} - Data: {log_data}")
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error logging frontend message: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Suppress SSL warnings for internal sites
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    app.run(debug=True, port=5001)
