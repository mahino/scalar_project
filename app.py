"""
Main Flask Application - Refactored with All Endpoints
Uses modular architecture with separate classes for different functionalities
"""

from flask import Flask, render_template, request, jsonify
import os
import re
import json
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime

# Import our custom modules
from modules.logging_manager import LoggingManager
from modules.storage_manager import StorageManager
from modules.payload_scaler import PayloadScaler
from modules.blueprint_generator import BlueprintGenerator
from modules.live_uuid_processor import LiveUuidProcessor
from modules.analyzer_manager import AnalyzerManager
from modules.api_logger import api_logger

# Initialize Flask app
app = Flask(__name__)

# Initialize managers
BASE_DIR = os.path.dirname(__file__)
logging_manager = LoggingManager(BASE_DIR)
logger = logging_manager.get_logger()

storage_manager = StorageManager(BASE_DIR, logger)
payload_scaler = PayloadScaler(logger)
blueprint_generator = BlueprintGenerator(logger)
live_uuid_processor = LiveUuidProcessor(logger)
analyzer_manager = AnalyzerManager(logger, BASE_DIR)

# ============================================================================
# BASIC ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main application page"""
    return render_template('index.html')

@app.route('/simplified')
def simplified_ui():
    """Simplified UI page"""
    return render_template('simplified_ui.html')

# ============================================================================
# API ROUTES - PAYLOAD GENERATION
# ============================================================================

@app.route('/api/payload/generate', methods=['POST'])
def generate_payload_from_rules():
    """Generate payload using rules and entity counts"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        api_url = data.get('api_url', 'blueprint')
        entity_counts = data.get('entity_counts', {})
        blueprint_type = data.get('blueprint_type', 'multi_vm')
        profile_options = data.get('profile_options', {})
        include_guest_customization = data.get('include_guest_customization', False)
        live_uuids = data.get('live_uuids', {})
        task_execution = data.get('task_execution', 'parallel')
        
        logger.info(f"Generate payload request - API: {api_url}, Entity counts: {entity_counts}")
        
        # Log the API request
        logging_manager.log_api_request_response(
            api_name='scalar_api_payload_generate',
            endpoint='/api/payload/generate',
            method='POST',
            request_data=data
        )
        
        # Process user input (handle both simplified and full formats)
        processed_request = payload_scaler.process_user_input_and_generate_payload(data)
        entity_counts = processed_request.get('entity_counts', entity_counts)
        
        # For blueprints, always generate from scratch using the blueprint generator
        if api_url == 'blueprint':
            logger.info("Generating blueprint from scratch using blueprint generator")
            
            # Extract counts for blueprint generation
            app_profiles = entity_counts.get('spec.resources.app_profile_list', 1)
            services = entity_counts.get('spec.resources.service_definition_list', 1)
            
            # Extract blueprint name from user input (optional)
            blueprint_name = data.get('blueprint_name')
            
            # Generate blueprint payload
            scaled_payload = blueprint_generator.generate_blueprint_payload(services, app_profiles, blueprint_name)
            
            # Apply hardcoded rules and fixes
            scaled_payload = blueprint_generator.fix_blueprint_deployment_references(scaled_payload)
            
            
        elif storage_manager.get_api_rule_set(api_url):
            # Use existing rules to scale payload for other APIs
            rule_set = storage_manager.get_api_rule_set(api_url)
            payload_template = rule_set.get('payload_template')
            if not payload_template:
                return jsonify({'error': f'No payload template found for API: {api_url}'}), 404
                
            # Scale the payload using our scaler
            scaled_payload = payload_scaler.scale_payload(payload_template, entity_counts)
            
        else:
            return jsonify({'error': f'No rules found for API: {api_url}'}), 404
                
        # Apply live UUIDs if provided
        print(f"Live UUIDs: {live_uuids}")
        if live_uuids and any(live_uuids.get(key, {}).get('uuid') for key in live_uuids):
            logger.info(f"Applying live UUIDs to payload: {json.dumps(live_uuids, indent=2)}")
            scaled_payload = live_uuid_processor.apply_live_uuids_to_payload(scaled_payload, live_uuids)
        logger.info(f"Scaled payload after live UUIDs: {json.dumps(scaled_payload, indent=2)}")
        logger.info(f"Scaled payload: {json.dumps(scaled_payload, indent=2)}")
        # Update metadata and spec names
        scaled_payload = payload_scaler.update_metadata_uuid(scaled_payload)
        scaled_payload = payload_scaler.update_spec_name(scaled_payload)
        
        # Add name suffixes to entities
        scaled_payload = payload_scaler.add_name_suffix_to_entities(scaled_payload, entity_counts)
        
        # Regenerate all UUIDs for uniqueness
        # scaled_payload = payload_scaler.regenerate_all_entity_uuids(scaled_payload)
        
        # Save response to history
        storage_manager.save_response_history(api_url, scaled_payload, entity_counts)
        
        # Log successful response
        logging_manager.log_api_request_response(
            api_name='scalar_api_payload_generate',
            endpoint='/api/payload/generate',
            method='POST',
            request_data=data,
            response_data={'status': 'success', 'payload_size': len(str(scaled_payload))},
            status_code=200
        )
        
        return jsonify({
            'scaled_payload': scaled_payload,
            'formatted_payload': str(scaled_payload),
            'entity_counts': entity_counts,
            'api_url': api_url
        })
        
    except Exception as e:
        logger.error(f"Error generating payload: {str(e)}")
        
        # Log error response
        logging_manager.log_api_request_response(
            api_name='scalar_api_payload_generate',
            endpoint='/api/payload/generate',
            method='POST',
            request_data=data if 'data' in locals() else None,
            error=str(e),
            status_code=500
        )
        
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate_payload():
    """Generate payload (legacy endpoint)"""
    return generate_payload_from_rules()

# ============================================================================
# API ROUTES - RULES MANAGEMENT
# ============================================================================

@app.route('/api/rules', methods=['GET'])
def list_all_api_rules():
    """List all API rules"""
    try:
        all_rules = storage_manager.load_api_rules()
        return jsonify(all_rules)
    except Exception as e:
        logger.error(f"Error listing API rules: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rules/<path:api_url>', methods=['GET'])
def get_rules_for_api(api_url):
    """Get rules for a specific API"""
    try:
        rule_set = storage_manager.get_api_rule_set(api_url)
        if rule_set:
            return jsonify(rule_set)
        else:
            return jsonify({'error': f'No rules found for API: {api_url}'}), 404
    except Exception as e:
        logger.error(f"Error getting rules for {api_url}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rules/<path:api_url>', methods=['DELETE'])
def delete_rules_for_api(api_url):
    """Delete rules for a specific API"""
    try:
        success = storage_manager.delete_api_rule_set(api_url)
        if success:
            return jsonify({'message': f'Rules deleted for API: {api_url}'})
        else:
            return jsonify({'error': f'No rules found for API: {api_url}'}), 404
    except Exception as e:
        logger.error(f"Error deleting rules for {api_url}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rules/analyze', methods=['POST'])
def analyze_for_rules():
    """Analyze a payload to detect scalable entities"""
    try:
        data = request.get_json()
        payload_data = data.get('payload')
        api_type = data.get('api_type', 'blueprint')
        
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
        
        # Find entities in the payload
        entities = payload_scaler.find_entities_in_payload(payload_data, api_type=api_type)
        id_values = payload_scaler.collect_all_id_values(payload_data)
        reference_map = payload_scaler.find_references(payload_data, id_values)
        
        entities_list = []
        for path, info in entities.items():
            entities_list.append({
                'path': path,
                'current_count': info['current_count'],
                'sample_item': info['sample_item']
            })
        
        response_data = {
            'success': True,
            'entities': entities_list,
            'original_payload': payload_data,
            'scalable_entity_paths': list(entities.keys()),
            'detected_api_type': api_type
        }
        
        # Log API request/response
        logging_manager.log_api_request_response(
            api_name="scalar_rules_analyze",
            endpoint="/api/rules/analyze",
            method="POST",
            request_data=data,
            response_data=response_data,
            status_code=200
        )
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Error analyzing payload: {str(e)}")
        error_response = {'error': f'Error analyzing payload: {str(e)}'}
        
        logging_manager.log_api_request_response(
            api_name="scalar_rules_analyze",
            endpoint="/api/rules/analyze",
            method="POST",
            request_data=data if 'data' in locals() else None,
            response_data=error_response,
            status_code=500,
            error=str(e)
        )
        
        return jsonify(error_response), 500

@app.route('/api/rules/save', methods=['POST'])
def save_rules_for_api():
    """Save rules for an API"""
    try:
        data = request.get_json()
        api_url = data.get('api_url')
        api_type = data.get('api_type', 'blueprint')
        rules = data.get('rules', [])
        payload_template = data.get('payload_template')
        scalable_entities = data.get('scalable_entities', [])
        task_execution = data.get('task_execution', 'parallel')
        
        if not api_url:
            return jsonify({'error': 'API URL is required'}), 400
        
        # Save the rule set
        storage_manager.save_api_rule_set(
            api_url=api_url,
            api_type=api_type,
            rules=rules,
            payload_template=payload_template,
            scalable_entities=scalable_entities,
            task_execution=task_execution
        )
        
        response_data = {
            'success': True,
            'message': f'Rules saved successfully for {api_url}',
            'api_url': api_url,
            'rules_count': len(rules)
        }
        
        # Log API request/response
        logging_manager.log_api_request_response(
            api_name="scalar_rules_save",
            endpoint="/api/rules/save",
            method="POST",
            request_data=data,
            response_data=response_data,
            status_code=200
        )
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Error saving rules: {str(e)}")
        error_response = {'error': f'Error saving rules: {str(e)}'}
        
        logging_manager.log_api_request_response(
            api_name="scalar_rules_save",
            endpoint="/api/rules/save",
            method="POST",
            request_data=data if 'data' in locals() else None,
            response_data=error_response,
            status_code=500,
            error=str(e)
        )
        
        return jsonify(error_response), 500

@app.route('/api/rules/preview', methods=['POST'])
def preview_with_rules():
    """Preview payload with rules applied"""
    try:
        data = request.get_json()
        api_url = data.get('api_url')
        entity_counts = data.get('entity_counts', {})
        
        if not api_url:
            return jsonify({'error': 'API URL is required'}), 400
        
        # Load rule set
        rule_set = storage_manager.get_api_rule_set(api_url)
        if not rule_set:
            return jsonify({'error': f'No rules found for API: {api_url}'}), 404
        
        payload_template = rule_set.get('payload_template')
        if not payload_template:
            return jsonify({'error': f'No payload template found for API: {api_url}'}), 404
        
        # Scale the payload
        scaled_payload = payload_scaler.scale_payload(payload_template, entity_counts)
        
        # Apply blueprint-specific fixes if needed
        if api_url == 'blueprint':
            scaled_payload = blueprint_generator.fix_blueprint_deployment_references(scaled_payload)
    
        response_data = {
        'success': True,
            'scaled_payload': scaled_payload,
            'entity_counts': entity_counts,
            'api_url': api_url
        }
        
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error previewing with rules: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rules/<path:api_url>/history', methods=['GET'])
def get_entity_history(api_url):
    """Get history for an entity"""
    try:
        history = storage_manager.load_entity_history(api_url)
        return jsonify({
            'entity_name': api_url,
            'history': history
        })
    except Exception as e:
        logger.error(f"Error getting history for {api_url}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rules/<path:api_url>/history/<int:version_index>', methods=['GET'])
def get_history_version_api(api_url, version_index):
    """Get specific version from history"""
    try:
        history_entry = storage_manager.get_history_version(api_url, version_index)
        if history_entry:
            return jsonify({
                'entity_name': api_url,
                'version_index': version_index,
                    'history_entry': history_entry
            })
        else:
            return jsonify({'error': f'Version {version_index} not found for {api_url}'}), 404
    except Exception as e:
        logger.error(f"Error getting history version for {api_url}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rules/<path:api_url>/restore/<int:version_index>', methods=['POST'])
def restore_entity_version(api_url, version_index):
    """Restore entity from history version"""
    try:
        success = storage_manager.restore_from_history(api_url, version_index)
        if success:
            return jsonify({
                'message': f'Successfully restored {api_url} from version {version_index}'
            })
        else:
            return jsonify({'error': f'Failed to restore {api_url} from version {version_index}'}), 400
    except Exception as e:
        logger.error(f"Error restoring {api_url} from version {version_index}: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# API ROUTES - ANALYSIS AND UTILITIES
# ============================================================================

@app.route('/api/analyze', methods=['POST'])
def analyze_payload():
    """Analyze payload to find entities"""
    try:
        data = request.get_json()
        if not data or 'payload' not in data:
            return jsonify({'error': 'No payload provided'}), 400
            
        payload = data['payload']
        api_type = data.get('api_type', 'blueprint')
        
        # Find entities in the payload
        entities = payload_scaler.find_entities_in_payload(payload, api_type=api_type)
    
        return jsonify({
                'entities': entities,
                'api_type': api_type
            })
        
    except Exception as e:
        logger.error(f"Error analyzing payload: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/payload/entities/<path:api_url>', methods=['GET'])
def get_entities_for_api(api_url):
    """Get entities for a specific API"""
    try:
        rule_set = storage_manager.get_api_rule_set(api_url)
        if not rule_set:
            return jsonify({'error': f'No rules found for API: {api_url}'}), 404
        
        payload_template = rule_set.get('payload_template')
        if not payload_template:
            return jsonify({'error': f'No payload template found for API: {api_url}'}), 404
        
        api_type = rule_set.get('api_type', 'blueprint')
        entities = payload_scaler.find_entities_in_payload(payload_template, api_type=api_type)
        
        entities_list = []
        for path, info in entities.items():
            entities_list.append({
                'path': path,
                'current_count': info['current_count'],
                'sample_item': info['sample_item']
            })
    
        return jsonify({
            'success': True,
            'api_url': api_url,
                'entities': entities_list
        })

    except Exception as e:
        logger.error(f"Error getting entities for {api_url}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/types', methods=['GET'])
def get_api_types():
    """Get supported API types"""
    try:
        return jsonify({
            'success': True,
                'api_types': storage_manager.api_types
    })
    except Exception as e:
        logger.error(f"Error getting API types: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/default-rules/<api_type>', methods=['GET'])
def get_default_rules(api_type):
    """Get default rules for an API type"""
    try:
        if api_type not in storage_manager.api_types:
            return jsonify({'error': f'Unsupported API type: {api_type}'}), 400
        
        default_rules = storage_manager.load_default_rules(api_type)
        return jsonify({
            'success': True,
            'api_type': api_type,
                'default_rules': default_rules
            })
    
    except Exception as e:
        logger.error(f"Error getting default rules for {api_type}: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# API ROUTES - CONFIGURATION
# ============================================================================

@app.route('/api/simplified-entity-config', methods=['GET'])
def get_simplified_entity_config():
    """Get simplified entity configuration for the UI"""
    simplified_config = {
        "user_inputs": [
            {
                "name": "services",
                "label": "Services",
                "description": "Number of services to create",
                "min_value": 1,
                "max_value": 10,
                "default_value": 2
            },
            {
                "name": "app_profiles", 
                "label": "App Profiles",
                "description": "Number of application profiles",
                "min_value": 1,
                "max_value": 5,
                "default_value": 2
            },
            {
                "name": "credentials",
                "label": "Credentials", 
                "description": "Number of credentials (usually 1)",
                "min_value": 1,
                "max_value": 3,
                "default_value": 1
            }
        ],
        "hardcoded_rules": [
            {
                "name": "Packages",
                "formula": "= App Profiles × Services",
                "description": "One package per deployment (cycles through services)",
                "icon": "📦"
            },
            {
                "name": "Deployments per Profile",
                "formula": "= Services",
                "description": "Each profile has deployments equal to service count",
                "icon": "🚀"
            },
            {
                "name": "Substrates",
                "formula": "= App Profiles × Services", 
                "description": "Total substrates calculated automatically",
                "icon": "🏗️"
            }
        ],
        "message": "Only the 3 user inputs above are editable. All other values are calculated automatically using hardcoded rules."
    }
    
    return jsonify(simplified_config)

@app.route('/api/log-frontend', methods=['POST'])
def log_frontend():
    """Log frontend messages"""
    try:
        data = request.get_json()
        level = data.get('level', 'info')
        message = data.get('message', '')
        context = data.get('context', {})
        
        # Log the frontend message
        if level == 'error':
            logger.error(f"Frontend: {message} | Context: {context}")
        elif level == 'warn':
            logger.warning(f"Frontend: {message} | Context: {context}")
        else:
            logger.info(f"Frontend: {message} | Context: {context}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error logging frontend message: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

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

# ============================================================================
# API ROUTES - LIVE UUID INTEGRATION
# ============================================================================

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
            logging_manager.log_api_request_response(
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
            logging_manager.log_api_request_response(
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
        logger.error(f"Exception in test_pc_connection: {str(e)}")
        error_response = {
            'success': False,
            'error': str(e)
        }
        
        # Log PC API exception
        logging_manager.log_api_request_response(
            api_name="pc_test_connection",
            endpoint="/api/live-uuid/test-connection",
            method="POST",
            request_data=data if 'data' in locals() else None,
            response_data=error_response,
            status_code=500,
            error=str(e)
        )
        
        return jsonify(error_response), 500

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
            
            response_data = {
                'success': True,
                'projects': projects,
                'total_matches': projects_data.get('metadata', {}).get('total_matches', 0)
            }
            
            # Log PC API request/response
            logging_manager.log_api_request_response(
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
            
            return jsonify(error_response), response.status_code
            
    except Exception as e:
        logger.error(f"Exception in get_projects: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
    """Get cluster names from live PC."""
    try:
        data = request.get_json()
        pc_url = data.get('pc_url', '')
        username = data.get('username', 'admin')
        password = data.get('password', 'Nutanix.123')
        
        logger.info(f"Fetching cluster names from PC: {pc_url}")
        
        if not pc_url:
            return jsonify({'error': 'PC URL is required'}), 400
        
        # Build API URL for clusters
        api_url = build_api_url(pc_url, 'dm', 'api/nutanix/v3/clusters/list')
        
        payload = {
            "length": 50,
            "offset": 0,
            "kind": "cluster"
        }
        
        # Create authenticated session
        session = requests.Session()
        session.auth = HTTPBasicAuth(username, password)
        session.headers = {'Content-Type': 'application/json'}
        session.verify = False
        
        response = session.post(api_url, json=payload, timeout=30)
                
        if response.status_code == 200:
            clusters_data = response.json()
            clusters = []
            for entity in clusters_data.get('entities', []):
                cluster = {
                    'uuid': entity.get('metadata', {}).get('uuid'),
                    'name': entity.get('spec', {}).get('name'),
                    'resources': entity.get('spec', {}).get('resources', {})
                }
                clusters.append(cluster)
        
            return jsonify({
                'success': True,
                    'clusters': clusters
            })
        else:
            return jsonify({'error': f'API call failed with status {response.status_code}'}), response.status_code
        
    except Exception as e:
        logger.error(f"Exception in get_cluster_names: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/live-uuid/images', methods=['POST'])
def get_images():
    """Get images list from live PC."""
    try:
        data = request.get_json()
        pc_url = data.get('pc_url', '')
        account_uuid = data.get('account_uuid', '')
        username = data.get('username', 'admin')
        password = data.get('password', 'Nutanix.123')
        
        logger.info(f"Fetching images from PC: {pc_url} for account: {account_uuid}")
        
        if not pc_url:
            return jsonify({'error': 'PC URL is required'}), 400
        if not account_uuid:
            return jsonify({'error': 'Account UUID is required'}), 400
        
        # Build API URL for images
        api_url = build_api_url(pc_url, 'ncm', 'api/nutanix/v3/nutanix/v1/groups/list')
        
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
        
        # Create authenticated session
        session = requests.Session()
        session.auth = HTTPBasicAuth(username, password)
        session.headers = {'Content-Type': 'application/json'}
        session.verify = False
        
        response = session.post(api_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            images_data = response.json()
            images = []
            for group in images_data.get('group_results', []):
                for entity in group.get('entity_results', []):
                    image = {
                        'uuid': entity.get('data', [{}])[0].get('values', [{}])[0].get('values', [''])[0],
                        'name': entity.get('data', [{}])[1].get('values', [{}])[0].get('values', [''])[0] if len(entity.get('data', [])) > 1 else '',
                        'type': entity.get('data', [{}])[2].get('values', [{}])[0].get('values', [''])[0] if len(entity.get('data', [])) > 2 else '',
                        'size': entity.get('data', [{}])[3].get('values', [{}])[0].get('values', [''])[0] if len(entity.get('data', [])) > 3 else ''
                    }
                    images.append(image)
            
            return jsonify({
                'success': True,
                'images': images
            })
        else:
            return jsonify({'error': f'API call failed with status {response.status_code}'}), response.status_code
            
    except Exception as e:
        logger.error(f"Exception in get_images: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# ANALYZER API ROUTES
# ============================================================================

@app.route('/api/analyzer/ssh-connect', methods=['POST'])
def analyzer_ssh_connect():
    """Test SSH connection to cluster"""
    try:
        data = request.get_json()
        pc_ip = data.get('pc_ip')
        cluster_type = data.get('cluster_type', 'pc')
        
        if not pc_ip:
            return jsonify({'error': 'IP address is required'}), 400
        
        logger.info(f"Testing SSH connection to {cluster_type} cluster {pc_ip}")
        result = analyzer_manager.ssh_connect(pc_ip, cluster_type)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"SSH connection error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyzer/kubeconfig-setup', methods=['POST'])
def analyzer_kubeconfig_setup():
    """Setup configuration for the cluster"""
    try:
        data = request.get_json()
        pc_ip = data.get('pc_ip')
        cluster_type = data.get('cluster_type', 'pc')
        
        if not pc_ip:
            return jsonify({'error': 'IP address is required'}), 400
        
        config_type = "kubeconfig" if cluster_type == "ncm" else "Docker"
        logger.info(f"Setting up {config_type} for {cluster_type} cluster {pc_ip}")
        result = analyzer_manager.setup_kubeconfig(pc_ip, cluster_type)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Kubeconfig setup error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyzer/discover-pods', methods=['POST'])
def analyzer_discover_pods():
    """Discover services (pods for NCM, containers for PC)"""
    try:
        data = request.get_json()
        pc_ip = data.get('pc_ip')
        cluster_type = data.get('cluster_type', 'pc')
        namespace = data.get('namespace', 'ntnx-ncm-selfservice')
        
        if not pc_ip:
            return jsonify({'error': 'IP address is required'}), 400
        
        service_type = "pods" if cluster_type == "ncm" else "containers"
        logger.info(f"Discovering {service_type} for {cluster_type} cluster {pc_ip}")
        result = analyzer_manager.discover_pods(pc_ip, cluster_type, namespace)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Pod discovery error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyzer/collect-logs', methods=['POST'])
def analyzer_collect_logs():
    """Collect logs from discovered services"""
    try:
        data = request.get_json()
        pc_ip = data.get('pc_ip')
        cluster_type = data.get('cluster_type', 'pc')
        namespace = data.get('namespace', 'ntnx-ncm-selfservice')
        pods = data.get('pods', [])
        
        if not pc_ip:
            return jsonify({'error': 'IP address is required'}), 400
        
        if not pods:
            return jsonify({'error': 'Service list is required'}), 400
        
        force_refresh = data.get('force_refresh', False)
        
        service_type = "pods" if cluster_type == "ncm" else "containers"
        logger.info(f"Collecting logs from {len(pods)} {service_type} for {cluster_type} cluster {pc_ip}")
        result = analyzer_manager.collect_logs(pc_ip, cluster_type, namespace, pods, force_refresh)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Log collection error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyzer/check-existing-logs', methods=['POST'])
def analyzer_check_existing_logs():
    """Check if logs already exist for this PC and cluster type"""
    try:
        data = request.get_json()
        pc_ip = data.get('pc_ip')
        cluster_type = data.get('cluster_type', 'pc')
        
        if not pc_ip:
            return jsonify({'error': 'IP address is required'}), 400
        
        logger.info(f"Checking existing logs for {cluster_type} cluster {pc_ip}")
        result = analyzer_manager._check_existing_logs(pc_ip, cluster_type)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Check existing logs error: {str(e)}")
        return jsonify({'exists': False, 'error': str(e)}), 500

@app.route('/api/analyzer/analyze-logs', methods=['POST'])
def analyzer_analyze_logs():
    """Analyze collected logs"""
    try:
        data = request.get_json()
        pc_ip = data.get('pc_ip')
        cluster_type = data.get('cluster_type', 'pc')
        
        if not pc_ip:
            return jsonify({'error': 'IP address is required'}), 400
        
        logger.info(f"Analyzing logs for {cluster_type} cluster {pc_ip}")
        result = analyzer_manager.analyze_logs(pc_ip, cluster_type)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Log analysis error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyzer/get-flow', methods=['POST'])
def analyzer_get_flow():
    """Get application flow diagram data"""
    try:
        data = request.get_json()
        pc_ip = data.get('pc_ip')
        cluster_type = data.get('cluster_type', 'pc')
        application_uuid = data.get('application_uuid')
        
        if not pc_ip:
            return jsonify({'error': 'IP address is required'}), 400
        
        if not application_uuid:
            return jsonify({'error': 'Application UUID is required'}), 400
        
        logger.info(f"Getting flow for application {application_uuid} on {cluster_type} cluster {pc_ip}")
        result = analyzer_manager.get_application_flow(pc_ip, application_uuid, cluster_type)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Flow retrieval error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyzer/cleanup', methods=['POST'])
def analyzer_cleanup():
    """Clean up analyzer workspace"""
    try:
        data = request.get_json()
        pc_ip = data.get('pc_ip')  # Optional - if not provided, cleans everything
        
        logger.info(f"Cleaning up analyzer workspace for {pc_ip if pc_ip else 'all'}")
        analyzer_manager.cleanup_workspace(pc_ip)
        
        return jsonify({
            'success': True,
            'message': f'Workspace cleaned up for {pc_ip if pc_ip else "all clusters"}'
        })
        
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyzer/cleanup-logs', methods=['POST'])
def analyzer_cleanup_logs():
    """Clean up log directories by removing folders and keeping only *.log* files"""
    try:
        data = request.get_json()
        pc_ip = data.get('pc_ip')
        directories = data.get('directories')  # Optional - defaults to standard log dirs
        
        if not pc_ip:
            return jsonify({'error': 'PC IP address is required'}), 400
        
        logger.info(f"Cleaning up log directories for {pc_ip}")
        result = analyzer_manager.cleanup_log_directories(pc_ip, directories)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Log cleanup error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# DASHBOARD API ENDPOINTS
# ============================================================================

@app.route('/api/dashboard/node-details', methods=['POST'])
def dashboard_get_node_details():
    """Fetch node details from Jarvis API"""
    start_time = datetime.now()
    request_data = request.get_json() or {}
    client_ip = request.remote_addr
    
    try:
        pool_id = request_data.get('pool_id')
        limit = request_data.get('limit', 25)
        page = request_data.get('page', 1)
        start = request_data.get('start', 0)
        
        if not pool_id:
            error_response = {'error': 'Pool ID is required'}
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log internal API call
            api_logger.log_internal_request(
                endpoint='/api/dashboard/node-details',
                method='POST',
                request_data=request_data,
                response_data=error_response,
                status_code=400,
                duration_ms=duration_ms,
                client_ip=client_ip
            )
            
            return jsonify(error_response), 400
        
        # Construct Jarvis API URL
        jarvis_url = f"https://jarvis.eng.nutanix.com/api/v2/pools/{pool_id}/node_details"
        params = {
            '_dc': int(datetime.now().timestamp() * 1000),
            'page': page,
            'start': start,
            'limit': limit
        }
        
        logger.info(f"Fetching node details from Jarvis API: {jarvis_url}")
        logger.info(f"Parameters: {params}")
        
        # For demo purposes, return mock data if pool_id is "demo"
        if pool_id == "demo":
            mock_nodes = [
                {
                    "is_enabled": True,
                    "comment": "Demo node for testing",
                    "name": "demo-node-1",
                    "cluster_created_at": {"$date": 1759311029435},
                    "cluster_owner": "demo.user",
                    "hardware": {
                        "mem": "540 GB",
                        "storage": [
                            {"model": "SAMSUNG SSD", "disk": "/dev/sda", "type": "SSD", "size": "1.92 TB"},
                            {"model": "SAMSUNG SSD", "disk": "/dev/sdb", "type": "SSD", "size": "1.92 TB"}
                        ],
                        "cpu_cores": "64",
                        "num_cpu_sockets": "2",
                        "position": "A",
                        "model": "NX-3060-G8",
                        "cpu": "Intel Xeon Silver 4314",
                        "credit_estimate": 100,
                        "serial": "DEMO123456"
                    },
                    "network_gateway": "10.46.116.1",
                    "_id": {"$oid": "demo123456789"},
                    "cluster_name": "demo_cluster"
                },
                {
                    "is_enabled": False,
                    "comment": "EOL node (Disabled for demo)",
                    "name": "demo-node-2",
                    "cluster_created_at": {"$date": 1746771421174},
                    "cluster_owner": "demo.admin",
                    "hardware": {
                        "mem": "270 GB",
                        "storage": [
                            {"model": "SAMSUNG MZ7KM960", "disk": "/dev/sda", "type": "SSD", "size": "960 GB"},
                            {"model": "ST2000NM0055", "disk": "/dev/sdb", "type": "HDD", "size": "2.0 TB"}
                        ],
                        "cpu_cores": "32",
                        "num_cpu_sockets": "2",
                        "position": "B",
                        "model": "NX-1065-G5",
                        "cpu": "Intel Xeon E5-2620 v4",
                        "credit_estimate": 165,
                        "serial": "DEMO789012"
                    },
                    "network_gateway": "10.46.208.1",
                    "_id": {"$oid": "demo789012345"},
                    "cluster_name": "demo_cluster_old"
                },
                {
                    "is_enabled": True,
                    "comment": "High memory node",
                    "name": "demo-node-3",
                    "cluster_created_at": {"$date": 1759311029435},
                    "cluster_owner": "demo.user",
                    "hardware": {
                        "mem": "472 GB",
                        "storage": [{"model": "SAMSUNG SSD", "disk": "/dev/sda", "type": "SSD", "size": "1.92 TB"}],
                        "cpu_cores": "48",
                        "num_cpu_sockets": "2",
                        "position": "C",
                        "model": "NX-3060-G7",
                        "cpu": "Intel Xeon Gold 6248R",
                        "credit_estimate": 120,
                        "serial": "DEMO345678"
                    },
                    "network_gateway": "10.46.116.1",
                    "_id": {"$oid": "demo345678901"},
                    "cluster_name": "demo_cluster"
                },
                {
                    "is_enabled": True,
                    "comment": "Medium memory node",
                    "name": "demo-node-4",
                    "cluster_created_at": {"$date": 1759311029435},
                    "cluster_owner": "demo.admin",
                    "hardware": {
                        "mem": "269 GB",
                        "storage": [{"model": "SAMSUNG SSD", "disk": "/dev/sda", "type": "SSD", "size": "960 GB"}],
                        "cpu_cores": "32",
                        "num_cpu_sockets": "2",
                        "position": "D",
                        "model": "NX-1065-G6",
                        "cpu": "Intel Xeon Silver 4210R",
                        "credit_estimate": 90,
                        "serial": "DEMO456789"
                    },
                    "network_gateway": "10.46.208.1",
                    "_id": {"$oid": "demo456789012"},
                    "cluster_name": "demo_cluster_old"
                },
                {
                    "is_enabled": True,
                    "comment": "Low memory node",
                    "name": "demo-node-5",
                    "cluster_created_at": {"$date": 1759311029435},
                    "cluster_owner": "demo.user",
                    "hardware": {
                        "mem": "67 GB",
                        "storage": [{"model": "SAMSUNG SSD", "disk": "/dev/sda", "type": "SSD", "size": "480 GB"}],
                        "cpu_cores": "16",
                        "num_cpu_sockets": "1",
                        "position": "E",
                        "model": "NX-1065-G4",
                        "cpu": "Intel Xeon E5-2630 v3",
                        "credit_estimate": 50,
                        "serial": "DEMO567890"
                    },
                    "network_gateway": "10.46.116.1",
                    "_id": {"$oid": "demo567890123"},
                    "cluster_name": "demo_cluster"
                },
                {
                    "is_enabled": True,
                    "comment": "High capacity node",
                    "name": "demo-node-6",
                    "cluster_created_at": {"$date": 1759311029435},
                    "cluster_owner": "demo.admin",
                    "hardware": {
                        "mem": "1024 GB",
                        "storage": [
                            {"model": "SAMSUNG SSD", "disk": "/dev/sda", "type": "SSD", "size": "3.84 TB"},
                            {"model": "SAMSUNG SSD", "disk": "/dev/sdb", "type": "SSD", "size": "3.84 TB"}
                        ],
                        "cpu_cores": "96",
                        "num_cpu_sockets": "2",
                        "position": "F",
                        "model": "NX-8155-G6",
                        "cpu": "Intel Xeon Platinum 8280",
                        "credit_estimate": 200,
                        "serial": "DEMO678901"
                    },
                    "network_gateway": "10.46.208.1",
                    "_id": {"$oid": "demo678901234"},
                    "cluster_name": "demo_cluster_premium"
                },
                {
                    "is_enabled": True,
                    "comment": "Ultra high memory node",
                    "name": "demo-node-7",
                    "cluster_created_at": {"$date": 1759311029435},
                    "cluster_owner": "demo.admin",
                    "hardware": {
                        "mem": "1081 GB",
                        "storage": [
                            {"model": "SAMSUNG SSD", "disk": "/dev/sda", "type": "SSD", "size": "7.68 TB"},
                            {"model": "SAMSUNG SSD", "disk": "/dev/sdb", "type": "SSD", "size": "7.68 TB"}
                        ],
                        "cpu_cores": "128",
                        "num_cpu_sockets": "2",
                        "position": "G",
                        "model": "NX-8155-G7",
                        "cpu": "Intel Xeon Platinum 8380",
                        "credit_estimate": 250,
                        "serial": "DEMO789012"
                    },
                    "network_gateway": "10.46.208.1",
                    "_id": {"$oid": "demo789012345"},
                    "cluster_name": "demo_cluster_premium"
                }
            ]
            
            demo_response = {
                'success': True,
                'nodes': mock_nodes,
                'total': len(mock_nodes),
                'page': page,
                'limit': limit,
                'demo_mode': True
            }
            
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log internal API call for demo mode
            api_logger.log_internal_request(
                endpoint='/api/dashboard/node-details',
                method='POST',
                request_data=request_data,
                response_data=demo_response,
                status_code=200,
                duration_ms=duration_ms,
                client_ip=client_ip
            )
            
            return jsonify(demo_response)
        
        # Make request to Jarvis API
        jarvis_start_time = datetime.now()
        response = None
        jarvis_error = None
        
        try:
            response = requests.get(jarvis_url, params=params, timeout=30, verify=False)
            jarvis_duration_ms = (datetime.now() - jarvis_start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                jarvis_data = response.json()
                
                # Based on the sample response, the structure is {"data": [...], "success": true}
                nodes = []
                total = 0
                
                if isinstance(jarvis_data, dict):
                    if 'data' in jarvis_data:
                        nodes = jarvis_data['data']
                        total = len(nodes)  # Calculate total from actual data length
                        
                        # Filter out disabled nodes if requested (optional)
                        # nodes = [node for node in nodes if node.get('is_enabled', True)]
                        
                        logger.info(f"Successfully fetched {len(nodes)} nodes from Jarvis API")
                        logger.info(f"Sample node keys: {list(nodes[0].keys()) if nodes else 'No nodes'}")
                        
                        # Log successful Jarvis API call
                        api_logger.log_jarvis_request(
                            url=jarvis_url,
                            method='GET',
                            params=params,
                            response_data=jarvis_data,
                            status_code=response.status_code,
                            duration_ms=jarvis_duration_ms
                        )
                        
                        success_response = {
                            'success': True,
                            'nodes': nodes,
                            'total': total,
                            'page': page,
                            'limit': limit,
                            'jarvis_success': jarvis_data.get('success', True)
                        }
                        
                        # Log internal API response
                        total_duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                        api_logger.log_internal_request(
                            endpoint='/api/dashboard/node-details',
                            method='POST',
                            request_data=request_data,
                            response_data=success_response,
                            status_code=200,
                            duration_ms=total_duration_ms,
                            client_ip=client_ip
                        )
                        
                        return jsonify(success_response)
                    else:
                        logger.warning(f"Unexpected Jarvis response structure: {list(jarvis_data.keys())}")
                        
                        # Log unexpected response structure
                        api_logger.log_jarvis_request(
                            url=jarvis_url,
                            method='GET',
                            params=params,
                            response_data=jarvis_data,
                            status_code=response.status_code,
                            duration_ms=jarvis_duration_ms,
                            error="Unexpected response structure"
                        )
                        
                        error_response = {'error': 'Unexpected response structure from Jarvis API'}
                    total_duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                    
                    api_logger.log_internal_request(
                        endpoint='/api/dashboard/node-details',
                        method='POST',
                        request_data=request_data,
                        response_data=error_response,
                        status_code=500,
                        duration_ms=total_duration_ms,
                        client_ip=client_ip
                    )
                    
                    return jsonify(error_response), 500
                else:
                    logger.warning(f"Jarvis response is not a dictionary: {type(jarvis_data)}")
                    
                    # Log invalid response format
                    api_logger.log_jarvis_request(
                        url=jarvis_url,
                        method='GET',
                        params=params,
                        response_data={"raw_response": str(jarvis_data)},  # Truncate for logging
                        status_code=response.status_code,
                        duration_ms=jarvis_duration_ms,
                        error="Invalid response format"
                    )
                    
                    error_response = {'error': 'Invalid response format from Jarvis API'}
                    total_duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                    
                    api_logger.log_internal_request(
                        endpoint='/api/dashboard/node-details',
                        method='POST',
                        request_data=request_data,
                        response_data=error_response,
                        status_code=500,
                        duration_ms=total_duration_ms,
                        client_ip=client_ip
                    )
                    
                    return jsonify(error_response), 500
            else:
                error_msg = f"Jarvis API returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                
                # Log failed Jarvis API call
                api_logger.log_jarvis_request(
                    url=jarvis_url,
                    method='GET',
                    params=params,
                    response_data={"error_text": response.text},  # Truncate for logging
                    status_code=response.status_code,
                    duration_ms=jarvis_duration_ms,
                    error=error_msg
                )
                
                error_response = {'error': error_msg}
                total_duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                
                api_logger.log_internal_request(
                    endpoint='/api/dashboard/node-details',
                    method='POST',
                    request_data=request_data,
                    response_data=error_response,
                    status_code=response.status_code,
                    duration_ms=total_duration_ms,
                    client_ip=client_ip
                )
                
                return jsonify(error_response), response.status_code
                
        except requests.exceptions.Timeout:
            jarvis_duration_ms = (datetime.now() - jarvis_start_time).total_seconds() * 1000
            error_msg = "Timeout while connecting to Jarvis API"
            logger.error(error_msg)
            
            # Log timeout error
            api_logger.log_jarvis_request(
                url=jarvis_url,
                method='GET',
                params=params,
                response_data=None,
                status_code=None,
                duration_ms=jarvis_duration_ms,
                error=error_msg
            )
            
            error_response = {'error': error_msg}
            total_duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            api_logger.log_internal_request(
                endpoint='/api/dashboard/node-details',
                method='POST',
                request_data=request_data,
                response_data=error_response,
                status_code=408,
                duration_ms=total_duration_ms,
                client_ip=client_ip
            )
            
            return jsonify(error_response), 408
            
        except requests.exceptions.ConnectionError:
            jarvis_duration_ms = (datetime.now() - jarvis_start_time).total_seconds() * 1000
            error_msg = "Failed to connect to Jarvis API"
            logger.error(error_msg)
            
            # Log connection error
            api_logger.log_jarvis_request(
                url=jarvis_url,
                method='GET',
                params=params,
                response_data=None,
                status_code=None,
                duration_ms=jarvis_duration_ms,
                error=error_msg
            )
            
            error_response = {'error': error_msg}
            total_duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            api_logger.log_internal_request(
                endpoint='/api/dashboard/node-details',
                method='POST',
                request_data=request_data,
                response_data=error_response,
                status_code=503,
                duration_ms=total_duration_ms,
                client_ip=client_ip
            )
            
            return jsonify(error_response), 503
            
    except Exception as e:
        error_msg = f"Dashboard API error: {str(e)}"
        logger.error(error_msg)
        
        # Log general error
        total_duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        error_response = {'error': error_msg}
        
        api_logger.log_internal_request(
            endpoint='/api/dashboard/node-details',
            method='POST',
            request_data=request_data,
            response_data=error_response,
            status_code=500,
            duration_ms=total_duration_ms,
            client_ip=client_ip
        )
        
        return jsonify(error_response), 500

@app.route('/api/dashboard/api-logs', methods=['GET'])
def dashboard_get_api_logs():
    """Get recent API logs for monitoring"""
    try:
        log_type = request.args.get('type', 'all')  # all, internal, external
        limit = int(request.args.get('limit', 20))
        
        logs = api_logger.get_recent_logs(log_type=log_type, limit=limit)
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': len(logs),
            'type': log_type
        })
        
    except Exception as e:
        logger.error(f"API logs error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/cleanup-logs', methods=['POST'])
def dashboard_cleanup_api_logs():
    """Clean up old API logs"""
    try:
        data = request.get_json() or {}
        days_to_keep = data.get('days_to_keep', 7)
        
        api_logger.cleanup_old_logs(days_to_keep=days_to_keep)
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up API logs older than {days_to_keep} days'
        })
        
    except Exception as e:
        logger.error(f"API logs cleanup error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/test-logging', methods=['POST'])
def dashboard_test_logging():
    """Test API logging functionality"""
    start_time = datetime.now()
    request_data = request.get_json() or {}
    client_ip = request.remote_addr
    
    try:
        # Simulate some processing
        import time
        time.sleep(0.1)  # 100ms delay
        
        response_data = {
            'success': True,
            'message': 'API logging test successful',
            'timestamp': datetime.now().isoformat(),
            'request_data': request_data
        }
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Log the API call
        api_logger.log_internal_request(
            endpoint='/api/dashboard/test-logging',
            method='POST',
            request_data=request_data,
            response_data=response_data,
            status_code=200,
            duration_ms=duration_ms,
            client_ip=client_ip
        )
        
        return jsonify(response_data)
        
    except Exception as e:
        error_response = {'error': str(e)}
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        api_logger.log_internal_request(
            endpoint='/api/dashboard/test-logging',
            method='POST',
            request_data=request_data,
            response_data=error_response,
            status_code=500,
            duration_ms=duration_ms,
            client_ip=client_ip
        )
        
        return jsonify(error_response), 500

# ============================================================================
# RDM API INTEGRATION ENDPOINTS
# ============================================================================

@app.route('/api/rdm/busy-resources', methods=['POST'])
def rdm_get_busy_resources():
    """Get busy resources from RDM API"""
    start_time = datetime.now()
    client_ip = request.remote_addr
    
    try:
        request_data = request.get_json()
        node_pool = request_data.get('node_pool', 'ncm_st')
        limit = request_data.get('limit', 100)
        node_ids = request_data.get('node_ids', [])
        
        if not node_ids:
            return jsonify({'error': 'node_ids are required', 'success': False}), 400
        
        # Build RDM API URL
        ids_param = ','.join(node_ids)
        rdm_url = f"https://rdm.eng.nutanix.com/api/v1/busy_resources/nodes?node_pool={node_pool}&limit={limit}&ids={ids_param}"
        
        logger.info(f"Calling RDM API: {rdm_url}")
        
        # Make request to RDM API
        response = requests.get(rdm_url, verify=False, timeout=600)
        response.raise_for_status()
        
        rdm_data = response.json()
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Log external API call
        api_logger.log_external_request(
            url=rdm_url,
            method='GET',
            request_data=request_data,
            response_data=rdm_data,
            status_code=response.status_code,
            duration_ms=duration_ms,
            service_name="rdm"
        )
        
        return jsonify({
            'success': True,
            'data': rdm_data.get('data', []),
            'total': len(rdm_data.get('data', [])),
            'node_pool': node_pool,
            'requested_ids': node_ids
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"RDM API request failed: {str(e)}")
        return jsonify({'error': f'RDM API request failed: {str(e)}', 'success': False}), 500
    except Exception as e:
        logger.error(f"Error in rdm_get_busy_resources: {str(e)}")
        return jsonify({'error': 'Internal server error', 'success': False}), 500

@app.route('/api/rdm/deployment-details', methods=['POST'])
def rdm_get_deployment_details():
    """Get deployment details from RDM API"""
    start_time = datetime.now()
    client_ip = request.remote_addr
    
    try:
        request_data = request.get_json()
        deployment_id = request_data.get('deployment_id')
        
        if not deployment_id:
            return jsonify({'error': 'deployment_id is required', 'success': False}), 400
        
        # Build RDM deployment API URL
        rdm_url = f"https://rdm.eng.nutanix.com/api/v1/deployments/{deployment_id}"
        
        logger.info(f"Calling RDM Deployment API: {rdm_url}")
        
        # Make request to RDM API
        response = requests.get(rdm_url, verify=False, timeout=600)
        response.raise_for_status()
        
        deployment_data = response.json()
        
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Log external API call
        api_logger.log_external_request(
            url=rdm_url,
            method='GET',
            request_data=request_data,
            response_data=deployment_data,
            status_code=response.status_code,
            duration_ms=duration_ms,
            service_name="rdm"
        )
        
        return jsonify({
            'success': True,
            'data': deployment_data.get('data', {}),
            'deployment_id': deployment_id
        })
        
    except requests.exceptions.RequestException as e:
        logger.error(f"RDM Deployment API request failed: {str(e)}")
        return jsonify({'error': f'RDM Deployment API request failed: {str(e)}', 'success': False}), 500
    except Exception as e:
        logger.error(f"Error in rdm_get_deployment_details: {str(e)}")
        return jsonify({'error': 'Internal server error', 'success': False}), 500

# ============================================================================
# MAIN APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    app.run(debug=True, host='0.0.0.0', port=5001)
