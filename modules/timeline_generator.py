#!/usr/bin/env python3
"""
Timeline Generator Module
Based on enhanced del.py - Generates complete timeline analysis for application UUIDs by analyzing all service logs.
Integrated with the scalar project analyzer system with dynamic service discovery.
"""

import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import logging


class AppTimelineGenerator:
    def __init__(self, nucalm_log_dir, epsilon_log_dir=None, logger=None):
        self.nucalm_log_dir = Path(nucalm_log_dir)
        self.epsilon_log_dir = Path(epsilon_log_dir) if epsilon_log_dir else None
        self.app_uuid = None
        self.reference_ids = {}
        self.timeline_events = []
        self.service_interactions = {}  # Track service-to-service calls
        self.logger = logger or logging.getLogger(__name__)
        
        # Define service directories - files will be discovered dynamically
        self.service_dirs = {
            'nucalm': self.nucalm_log_dir,
            'epsilon': self.epsilon_log_dir
        }
        
        # Discover all log files dynamically
        self.service_logs = self._discover_service_logs()
    
    def _discover_service_logs(self):
        """Dynamically discover all log files in both directories"""
        discovered_logs = {}
        
        # Service name mappings based on log file patterns (*.log*)
        service_patterns = {
            'styx': r'^styx\.log',
            'jove': r'^jove\.log',
            'hercules': r'^hercules\.log',
            'algalon': r'^algalon\.log',
            'iris': r'^iris\.log',
            'eos': r'^eos\.log',
            'helios': r'^helios\.log',
            'pulsecollector': r'^pulsecollector\.log',
            'superevents': r'^superevents\.log',
            'epsilon_jove': r'^jove\.log',
            'durga': r'^durga_\d+\.log',
            'gozaffi': r'^gozaffi_\d+\.log',
            'indra': r'^indra_\d+\.log',
            'arjun': r'^arjun_\d+\.log',
            'karan': r'^karan_\d+\.log',
            'narad': r'^narad\.log',
            'vajra': r'^vajra_\d+\.log',
            'proxy_service': r'^proxy_service\.log',
            'redis': r'^redis\.log',
            'postgresql': r'^postgresql\.log',
            'opensearch': r'^opensearch\.log',
        }
        
        # Scan NUCALM directory
        if self.nucalm_log_dir and self.nucalm_log_dir.exists():
            for log_file in self.nucalm_log_dir.glob('*.log*'):
                if log_file.is_file() and not log_file.name.endswith('.xz'):
                    for service, pattern in service_patterns.items():
                        if service.startswith('epsilon_'):
                            continue  # Skip epsilon services for nucalm dir
                        if re.match(pattern, log_file.name):
                            if service not in discovered_logs:
                                discovered_logs[service] = {'dir': 'nucalm', 'files': []}
                            discovered_logs[service]['files'].append(log_file.name)
                            break
        
        # Scan EPSILON directory
        if self.epsilon_log_dir and self.epsilon_log_dir.exists():
            for log_file in self.epsilon_log_dir.glob('*.log*'):
                if log_file.is_file() and not log_file.name.endswith('.xz'):
                    for service, pattern in service_patterns.items():
                        # For epsilon directory, map jove to epsilon_jove
                        service_name = service
                        if service == 'jove':
                            service_name = 'epsilon_jove'
                        elif service.startswith('epsilon_'):
                            continue  # Skip epsilon_ prefixed services for direct matching
                            
                        if re.match(pattern, log_file.name):
                            if service_name not in discovered_logs:
                                discovered_logs[service_name] = {'dir': 'epsilon', 'files': []}
                            discovered_logs[service_name]['files'].append(log_file.name)
                            break
                    
                    # Handle epsilon-specific services
                    for service in ['durga', 'gozaffi', 'indra', 'arjun', 'karan', 'narad', 'vajra']:
                        pattern = service_patterns[service]
                        if re.match(pattern, log_file.name):
                            if service not in discovered_logs:
                                discovered_logs[service] = {'dir': 'epsilon', 'files': []}
                            discovered_logs[service]['files'].append(log_file.name)
                            break
        
        return discovered_logs
        
    def find_reference_ids(self, app_uuid):
        """Find all reference IDs associated with the app UUID"""
        print(f"🔍 Searching for reference IDs for app UUID: {app_uuid}")
        
        # Search in STYX logs for APP-CREATE entries
        if 'styx' not in self.service_logs:
            print("❌ STYX service logs not found")
            return False
            
        for log_file in self.service_logs['styx']['files']:
            log_path = self.nucalm_log_dir / log_file
            if not log_path.exists():
                continue
                
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                for _, line in enumerate(f, 1):
                    if app_uuid in line and 'APP-CREATE' in line:
                        # Extract reference IDs from the line
                        cr_match = re.search(r'\[cr:([a-f0-9-]+)\]', line)
                        pr_match = re.search(r'\[pr:([a-f0-9-]+)\]', line)
                        rr_match = re.search(r'\[rr:([a-f0-9-]+)\]', line)
                        
                        if cr_match:
                            self.reference_ids['cr'] = cr_match.group(1)
                        if pr_match:
                            self.reference_ids['pr'] = pr_match.group(1)
                        if rr_match:
                            self.reference_ids['rr'] = rr_match.group(1)
                            
                        # Extract timestamp and blueprint info
                        timestamp_match = re.search(r'\[(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{3,6})?Z?)\]', line)
                        bp_match = re.search(r'\[BP-([a-f0-9-]+):' + app_uuid, line)
                        
                        if timestamp_match:
                            self.reference_ids['timestamp'] = timestamp_match.group(1)
                        if bp_match:
                            self.reference_ids['blueprint_uuid'] = bp_match.group(1)
                            
                        break
        
        print(f"✅ Found reference IDs: {self.reference_ids}")
        return len(self.reference_ids) > 0
    
    def extract_timeline_events(self):
        """Extract timeline events from all service logs"""
        print("📊 Extracting timeline events from all services...")
        
        # Define patterns for all services - comprehensive patterns from enhanced del.py
        patterns = {
            # NUCALM Services
            'styx': [
                # Application Lifecycle
                (r'APP-CREATE-START', 'App Create Start', 'Apps API'),
                (r'APP-CREATE-END', 'App Create End', 'Apps API'),
                (r'APP-LAUNCH-START', 'App Launch Start', 'Apps API'),
                (r'APP-LAUNCH-END', 'App Launch End', 'Apps API'),
                (r'APP-DELETE-START', 'App Delete Start', 'Apps API'),
                (r'APP-DELETE-END', 'App Delete End', 'Apps API'),
                
                # Authentication & User Management
                (r'Username: from session ([^,]+), converted:([^,]+)', 'User Session Extract', 'Session Manager'),
                (r'username dump: g:([^,]+), type:', 'Username Processing', 'User Handler'),
                (r'Sending IAMv2 GET request: https://iam-proxy\.ntnx-base:8445/api/iam/v4\.0/authn/users/([a-f0-9-]+)', 'IAMv2 User Request', 'IAMv2 Service'),
                (r'IAMv2 response received', 'IAMv2 Response', 'IAMv2 Service'),
                (r'User authentication successful', 'Auth Success', 'Auth Service'),
                (r'User authentication failed', 'Auth Failed', 'Auth Service'),
                
                # Policy Management
                (r'Not raising policy down error', 'Policy Check Skip', 'Policy Helper'),
                (r'Policy validation started', 'Policy Validation', 'Policy Service'),
                (r'Policy approved for operation', 'Policy Approved', 'Policy Service'),
                (r'Policy rejected for operation', 'Policy Rejected', 'Policy Service'),
                (r'Policy service unavailable', 'Policy Down', 'Policy Service'),
                
                # Blueprint & Application Management
                (r'owner_reference not received, sending current logged in user as owner reference for the app', 'Owner Reference Set', 'Blueprint Launch'),
                (r'Fetching project by name: ([^\\s]+)', 'Project Lookup', 'Project Service'),
                (r'Project ([^\\s]+) found with UUID ([a-f0-9-]+)', 'Project Found', 'Project Service'),
                (r'Calling out bp launch with categories \{(.*?)\} and project_reference \{(.*?)\}', 'Blueprint Launch Call', 'Blueprint Launch API'),
                (r'Blueprint launch request prepared', 'BP Launch Prep', 'Blueprint Service'),
                (r'Blueprint validation started', 'BP Validation', 'Blueprint Service'),
                (r'Blueprint compilation complete', 'BP Compile', 'Blueprint Service'),
                
                # Service Interface Management
                (r'In get hercules local master handle method , scaleout mode ([^,]+)', 'Hercules Init', 'Hercules Interface'),
                (r'Hercules connection established', 'Hercules Connected', 'Hercules Interface'),
                (r'Hercules request sent', 'Hercules Request', 'Hercules Interface'),
                (r'Hercules response received', 'Hercules Response', 'Hercules Interface'),
                
                # Jove Interface Operations
                (r'session created', 'Jove Session Created', 'Jove Interface'),
                (r'Request- \'POST\' at \'blueprint/([a-f0-9-]+)/launch\?duplicate_check=False\'', 'Jove BP Launch Request', 'Jove Interface'),
                (r'Request- \'POST\' at \'([^\']+)\'', 'Jove POST Request', 'Jove Interface'),
                (r'Request- \'GET\' at \'([^\']+)\'', 'Jove GET Request', 'Jove Interface'),
                (r'Request- \'PUT\' at \'([^\']+)\'', 'Jove PUT Request', 'Jove Interface'),
                (r'Response- \'.*ergon_task_id\': \'([a-f0-9-]+)\'.*\'', 'Jove Ergon Response', 'Jove Interface'),
                (r'Response- \'.*duplicate_request\': (True|False).*\'', 'Jove Duplicate Check', 'Jove Interface'),
                (r'Response- \'.*status.*200.*\'', 'Jove Success Response', 'Jove Interface'),
                (r'Response- \'.*error.*\'', 'Jove Error Response', 'Jove Interface'),
                
                # Application Profile & Resource Management
                (r'for app-profile ([a-f0-9-]+), not_verified_account_names is ([^,]+)', 'App Profile Validation', 'App Profile Service'),
                (r'substrate_names_with_missing_account is ([^\\s]+)', 'Substrate Account Check', 'Resource Validator'),
                (r'accounts_not_whitelisted is ([^\\s]+)', 'Account Whitelist Check', 'Security Validator'),
                (r'Resource validation passed', 'Resource Validation', 'Resource Manager'),
                (r'Resource allocation started', 'Resource Allocation', 'Resource Manager'),
                
                # Category & Project Management
                (r'categories \{\'Project\': \'([^\']+)\'\}', 'Project Category Set', 'Category Manager'),
                (r'project_reference \{\'kind\': \'project\', \'name\': \'([^\']+)\', \'uuid\': \'([a-f0-9-]+)\'\}', 'Project Reference Set', 'Project Manager'),
                (r'Category assignment completed', 'Category Complete', 'Category Manager'),
                
                # Error Handling & Logging
                (r'Error occurred in blueprint launch: (.+)', 'BP Launch Error', 'Error Handler'),
                (r'Exception caught during app creation: (.+)', 'App Create Exception', 'Error Handler'),
                (r'Validation failed: (.+)', 'Validation Error', 'Validator'),
                (r'Timeout occurred during (.+)', 'Operation Timeout', 'Timeout Handler'),
                
                # Performance & Monitoring
                (r'Blueprint launch took (\d+)ms', 'BP Launch Performance', 'Performance Monitor'),
                (r'Project lookup took (\d+)ms', 'Project Lookup Performance', 'Performance Monitor'),
                (r'Authentication took (\d+)ms', 'Auth Performance', 'Performance Monitor'),
                (r'Total request processing time: (\d+)ms', 'Request Performance', 'Performance Monitor'),
                
                # Database Operations
                (r'Database query executed successfully', 'DB Query Success', 'Database Service'),
                (r'Database transaction started', 'DB Transaction Start', 'Database Service'),
                (r'Database transaction committed', 'DB Transaction Commit', 'Database Service'),
                (r'Database connection established', 'DB Connection', 'Database Service'),
                (r'os_query_handler_interface.*POST', 'OS Registration', 'Object Store'),
                (r'saveing Application object', 'DB Save', 'Database'),
            ],
            'jove': [
                (r'Got blueprint launch request', 'Blueprint Handler', 'Hercules Router'),
                (r'Got action run request', 'Run Handler', 'Hercules Router'),
                (r'request id provided.*WALed task identity', 'Task Creation', 'Ergon Utils'),
                (r'ergon_task_create with time.*msec', 'Ergon Task Stats', 'Ergon Utils'),
                (r'ergon\.TaskCreate with time.*msec', 'Ergon Task', 'Ergon Service'),
                (r'Blueprint launch ergon task created', 'Task Confirmation', 'Hercules Router'),
                (r'sending request packet over channel', 'Request Dispatch', 'Request Dispatcher'),
                (r'Anycast message', 'Message Routing', 'Request Dispatcher'),
                (r'get worker message', 'Worker Selection', 'Worker Manager'),
                (r'Got worker.*hercules-.*-.*-.*-.*-', 'Worker Assigned', 'Worker Manager'),
                (r'old state ACTIVE new state BUSY', 'Worker State Change', 'Worker'),
                (r'Sending request Replayable.*worker router', 'Request Forward', 'Worker'),
                (r'Sending request over incoming channel', 'Channel Forward', 'Worker'),
                (r'workerHTTPHandler.*POST.*blueprint.*launch', 'HTTP Handler', 'Worker Listener'),
                (r'workerHTTPHandler.*POST.*apps.*run', 'HTTP Handler', 'Worker Listener'),
                (r'GetWorkerStateWithWorkerID with time.*msec', 'DB Operation', 'Worker State'),
                (r'Save WorkerState with time.*msec', 'DB Save', 'Worker State'),
                (r'Got publish data request', 'Publish Handler', 'Data Publisher'),
                (r'Unicast local message', 'Local Message', 'Message Router'),
                (r'stats item: ergon_task_create with time: (\d+) msec', 'Ergon Task Stats', 'Ergon Utils'),
            ],
            'hercules': [
                # Ergon Operations
                (r'Creating stub for Ergon on ergonip: (\d+)', 'Ergon Stub Creation', 'Ergon Service'),
                (r'Resolving hostname ergonip to IP', 'Hostname Resolution', 'Network Service'),
                (r'Updated wal and workstate milestone to (\d+) and marked task to (\d+)', 'Milestone Update', 'Ergon Helper'),
                (r'Updated wal and workstate milestone', 'Milestone Update', 'Ergon Helper'),
                (r'Ergon task created successfully', 'Ergon Task Created', 'Ergon Service'),
                
                # Database Operations
                (r'############### query executed properly ###############', 'DB Query Success', 'Database Service'),
                (r'Database connection established', 'DB Connection', 'Database Service'),
                (r'Transaction committed', 'DB Transaction', 'Database Service'),
                
                # Policy Management
                (r'Policy feature is enabled, adding policy task', 'Policy Task Add', 'Policy Helper'),
                (r'Policy config ips are \[(.*?)\]', 'Policy Config', 'Vidura Interface'),
                (r'plum request body', 'Policy Request', 'Policy Engine'),
                (r'SUCCESS.*APPROVED', 'Policy Approved', 'Policy Engine'),
                (r'FAILED.*REJECTED', 'Policy Rejected', 'Policy Engine'),
                (r'Policy evaluation complete', 'Policy Complete', 'Policy Engine'),
                
                # Quota & Resource Management
                (r'Making api call to fetch size for ([a-f0-9-]+) image', 'Image Size Request', 'Quota Helper'),
                (r'ahv_image_uuid_size_map \{(.*?)\}', 'Image Size Map', 'Quota Helper'),
                (r'Quota validation passed', 'Quota Validation', 'Quota Helper'),
                (r'Resource allocation started', 'Resource Allocation', 'Resource Manager'),
                
                # API Requests & Responses (Outgoing)
                (r'Request- \'POST\' at \'indra/sync/ImageInfo\?duplicate_check=False\'', 'Image Info Request', 'Indra Service'),
                (r'Request- \'POST\' at \'indra/sync/([^\']+)\'', 'Indra Sync Request', 'Indra Service'),
                (r'Request- \'GET\' at \'([^\']+)\'', 'HTTP GET Request', 'HTTP Client'),
                (r'Request- \'POST\' at \'([^\']+)\'', 'HTTP POST Request', 'HTTP Client'),
                (r'Request- \'PUT\' at \'([^\']+)\'', 'HTTP PUT Request', 'HTTP Client'),
                
                # API Responses (Incoming)
                (r'Response- \'.*\"image_size_bytes\":(\d+).*\'', 'Image Size Response', 'Indra Service'),
                (r'Response- \'.*\"status\": \"200 OK\".*\'', 'HTTP 200 Response', 'HTTP Client'),
                (r'Response- \'.*\"statusInt\": 200.*\'', 'HTTP Success Response', 'HTTP Client'),
                (r'Response- \'.*\"statusInt\": ([4-5]\d{2}).*\'', 'HTTP Error Response', 'HTTP Client'),
                
                # Blueprint & Application Management
                (r'Cloning the BP', 'Blueprint Clone', 'Blueprint Helper'),
                (r'Blueprint validation started', 'Blueprint Validation', 'Blueprint Service'),
                (r'Blueprint compilation complete', 'Blueprint Compile', 'Blueprint Service'),
                (r'Application launch initiated', 'App Launch Start', 'Application Service'),
                (r'Application provisioning started', 'App Provision Start', 'Application Service'),
                
                # Service Discovery & Communication
                (r'Service discovery for ([a-zA-Z_]+)', 'Service Discovery', 'Service Registry'),
                (r'Calling service ([a-zA-Z_]+) with endpoint ([^\\s]+)', 'Service Call', 'Service Client'),
                (r'Service ([a-zA-Z_]+) responded with status (\d+)', 'Service Response', 'Service Client'),
                
                # Task & Workflow Management
                (r'Task ([a-f0-9-]+) created', 'Task Creation', 'Task Manager'),
                (r'Task ([a-f0-9-]+) started', 'Task Start', 'Task Manager'),
                (r'Task ([a-f0-9-]+) completed', 'Task Complete', 'Task Manager'),
                (r'Workflow step (\d+) executing', 'Workflow Step', 'Workflow Engine'),
                (r'Workflow completed successfully', 'Workflow Success', 'Workflow Engine'),
                
                # Error Handling & Logging
                (r'Error occurred: (.+)', 'Error Handler', 'Error Service'),
                (r'Exception caught: (.+)', 'Exception Handler', 'Error Service'),
                (r'Retry attempt (\d+) for operation', 'Retry Operation', 'Retry Handler'),
                (r'Operation timeout after (\d+)ms', 'Operation Timeout', 'Timeout Handler'),
                
                # Authentication & Security
                (r'JWT token validation', 'JWT Validation', 'Auth Service'),
                (r'User authentication successful', 'Auth Success', 'Auth Service'),
                (r'Authorization check passed', 'Auth Check', 'Auth Service'),
                (r'Security policy applied', 'Security Policy', 'Security Service'),
            ],
            
            # EPSILON Services
            'epsilon_jove': [
                # Request Handlers
                (r'Got blueprint launch request', 'Blueprint Handler', 'Epsilon Jove Router'),
                (r'Got action run request', 'Run Handler', 'Epsilon Jove Router'),
                (r'Got publish data request', 'Publish Handler', 'Epsilon Data Publisher'),
                
                # Ergon Task Management
                (r'request id provided.*WALed task identity', 'Task Creation', 'Epsilon Ergon Utils'),
                (r'ergon_task_create with time.*msec', 'Ergon Task Stats', 'Epsilon Ergon Utils'),
                (r'ergon\.TaskCreate with time.*msec', 'Ergon Task', 'Epsilon Ergon Service'),
                (r'Blueprint launch ergon task created', 'Task Confirmation', 'Epsilon Jove Router'),
                (r'stats item: ergon_task_create with time: (\d+) msec', 'Ergon Task Stats', 'Epsilon Ergon Utils'),
                
                # Request Dispatching
                (r'sending request packet over channel', 'Request Dispatch', 'Epsilon Request Dispatcher'),
                (r'Sending request Replayable to worker router for book keeping', 'Request Forward', 'Epsilon Worker'),
                (r'Sending request over incoming channel', 'Channel Forward', 'Epsilon Worker'),
                
                # Message Routing
                (r'Anycast message', 'Message Routing', 'Epsilon Request Dispatcher'),
                (r'Unicast local message', 'Local Message', 'Epsilon Message Router'),
                (r'Unicast remote message', 'Remote Message', 'Epsilon Message Router'),
                (r'Multicast message', 'Multicast', 'Epsilon Message Router'),
                (r'Broadcast message', 'Broadcast', 'Epsilon Message Router'),
                
                # Worker Management
                (r'get worker message', 'Worker Selection', 'Epsilon Worker Manager'),
                (r'Got worker.*hercules-.*-.*-.*-.*-', 'Worker Assigned', 'Epsilon Worker Manager'),
                (r'old state ACTIVE new state BUSY', 'Worker State Change', 'Epsilon Worker'),
                
                # HTTP Handlers
                (r'workerHTTPHandler.*POST.*blueprint.*launch', 'HTTP Handler', 'Epsilon Worker Listener'),
                (r'workerHTTPHandler.*POST.*apps.*run', 'HTTP Handler', 'Epsilon Worker Listener'),
                
                # Response Handling
                (r'Jove Response', 'Jove Response', 'Epsilon Response Handler'),
                
                # Database Operations
                (r'GetWorkerStateWithWorkerID with time.*msec', 'DB Operation', 'Epsilon Worker State'),
                (r'Save WorkerState with time.*msec', 'DB Save', 'Epsilon Worker State'),
            ],
            'durga': [
                # Core Operations
                (r'Starting new root Span', 'Span Creation', 'Tracing Service'),
                (r'New workflow.*request in durga', 'Workflow Request', 'Workflow Engine'),
                (r'New runtask start request in durga', 'Run Task Start', 'Task Manager'),
                
                # Ergon & Task Management
                (r'Update to ergon started.*updating to milestome', 'Ergon Update Start', 'Ergon Service'),
                (r'Update to ergon done', 'Ergon Update Complete', 'Ergon Service'),
                (r'Setting TRLID from context', 'TRL Setup', 'Runlog Engine'),
                (r'Setting up trl properties', 'TRL Properties', 'Runlog Engine'),
                (r'Creating new runblock for trl type', 'Runblock Creation', 'Runlog Engine'),
                (r'Setting up properties on the runblock', 'Runblock Properties', 'Property Manager'),
                
                # Service Calls & Notifications
                (r'Sending Message /runlog/send_notifications', 'Notification Send', 'Runlog Service'),
                (r'Sending Message /runlog/v2/action', 'Runlog Action', 'Runlog Service'),
                (r'Sending Message /indra/run_cloud_task', 'Cloud Task Request', 'Indra Service'),
                (r'Sending Message /durga/run/.*/runtask/.*/start', 'Internal Task Start', 'Durga Internal'),
                
                # Workflow & Context
                (r'Created Workflow TRL from Task', 'Workflow TRL Creation', 'Workflow Engine'),
                (r'Request body for workflow start', 'Workflow Start Body', 'Workflow Engine'),
                (r'Expanded notification data', 'Notification Data', 'Notification Handler'),
                (r'Start request.*task_id.*trl_id', 'Task Start Request', 'Task Executor'),
                
                # Policy & Cloud Operations
                (r'Cloud payload.*vidura.*policy_execute', 'Policy Execution', 'Vidura Service'),
                (r'Cloud payload output', 'Policy Response', 'Vidura Service'),
                (r'provider_operation_payload', 'Provider Operation', 'Cloud Provider'),
                
                # Error Handling
                (r'Error in request processing', 'Request Error', 'Error Handler'),
                (r'Skipping properties.*because', 'Property Skip', 'Property Manager'),
                
                # Entity & Resource Management
                (r'Setting entity using default ID', 'Entity Setup', 'Entity Manager'),
                (r'Setting default entity on trl', 'Default Entity', 'Entity Manager'),
                (r'wf_res_entity.*wf_res_machine', 'Resource Setup', 'Resource Manager'),
            ],
            'gozaffi': [
                # Logger and Request Management
                (r'logger initialized for RequestID:', 'Logger Init', 'Logger Service'),
                (r'Response code: (\d+)', 'HTTP Response', 'HTTP Handler'),
                (r'Committing DB Session', 'DB Commit', 'Database Service'),
                
                # Task Management
                (r'Got Task for uuid: ([a-f0-9-]+)', 'Task Retrieval', 'Task Service'),
                (r'Updated workflow with task ID: ([a-f0-9-]+)', 'Workflow Update', 'Workflow Service'),
                
                # Service Creation Operations
                (r'Create Common Task Service started', 'Common Task Start', 'Task Service'),
                (r'Create Meta Service started', 'Meta Service Start', 'Meta Service'),
                (r'Create Callwf Service started', 'Callwf Service Start', 'Workflow Service'),
                (r'Update DAG Service started', 'DAG Update Start', 'DAG Service'),
                (r'Create DAG Service started', 'DAG Create Start', 'DAG Service'),
                (r'Create Loop Service started', 'Loop Service Start', 'Loop Service'),
                (r'Create Consolidate Props Service started', 'Props Consolidate Start', 'Property Service'),
                (r'Create Cloud Service started', 'Cloud Service Start', 'Cloud Service'),
                (r'Workflow Create service started', 'Workflow Create Start', 'Workflow Service'),
                (r'Workflow Create service ended', 'Workflow Create End', 'Workflow Service'),
                (r'Workflow Create all service started', 'Workflow Create All Start', 'Workflow Service'),
                (r'Workflow Create all service ended', 'Workflow Create All End', 'Workflow Service'),
                
                # Entity Management
                (r'Got Entity for uuid: ([a-f0-9-]+)', 'Entity Retrieval', 'Entity Service'),
                (r'Created Entity with UUID: ([a-f0-9-]+)', 'Entity Creation', 'Entity Service'),
                (r'GetEntityByName.*sql: no rows in result set', 'Entity Not Found', 'Entity Service'),
                (r'error response: Entity for id/name .* doesn\'t exist', 'Entity Missing Error', 'Error Handler'),
                
                # Credential Management
                (r'Got Credential for uuid: ([a-f0-9-]+)', 'Credential Retrieval', 'Credential Service'),
                (r'Got Credential for name: .* \(([a-f0-9-]+)\)', 'Credential Name Lookup', 'Credential Service'),
                (r'Updated Credential: 0x[a-f0-9]+', 'Credential Update', 'Credential Service'),
                (r'Updated Props for Creds id: ([a-f0-9-]+)', 'Credential Props Update', 'Property Service'),
                (r'Deleted \d+ props for Creds id: ([a-f0-9-]+)', 'Credential Props Delete', 'Property Service'),
                
                # Property Management
                (r'Created property .* for Entity id: ([a-f0-9-]+)', 'Property Creation', 'Property Service'),
                
                # Error Handling
                (r'strconv\.ParseBool: parsing "": invalid syntax', 'Parse Error', 'Error Handler'),
                
                # Legacy patterns (keeping for compatibility)
                (r'sql: no rows in result set', 'DB Query Empty', 'Database'),
                (r'Entity for.*doesn\'t exist', 'Entity Not Found', 'Entity Repository'),
                (r'GET.*entities.*get_by_name.*Executing Request', 'Entity Lookup', 'Gozaffi API'),
            ],
            'indra': [
                # Core Sync Operations
                (r'Sync request to indra worker', 'Sync Request', 'Indra Worker'),
                (r'Got sync request with data', 'Sync Handler', 'Provider Master'),
                (r'In GetSyncProviderHandler.*type NTNX', 'Provider Handler', 'Sync Provider'),
                (r'Initializing SyncProviderHandler', 'Provider Init', 'Sync Provider'),
                (r'ntnx provider data = \+&\{ValidatePlatformData', 'Platform Validation Data', 'NTNX Provider'),
                (r'ntnx provider data = \+&\{ImageInfo', 'Image Info Data', 'NTNX Provider'),
                
                # Server Configuration
                (r'Creating the Server Config object', 'Server Config', 'Config Manager'),
                (r'EnableCertAuth flag value is false', 'Cert Auth Config', 'Auth Manager'),
                (r'JWT provided and is not remote account', 'JWT Auth', 'Auth Manager'),
                (r'UserInfo is nil\. Getting userinfo from jwt', 'User Info Extract', 'Auth Manager'),
                (r'UserInfo: \{UserName:.*UserType:.*UserUUID:', 'User Info Setup', 'Auth Manager'),
                (r'Using onprem certs for v4 api clients', 'Cert Setup', 'Cert Manager'),
                
                # Platform Operations
                (r'Spec Cluster UUID:.*platform Subnet Cluster UUID:', 'Cluster UUID Validation', 'Cluster Service'),
                (r'Platfrom validation info is:', 'Platform Validation Info', 'Platform Service'),
                (r'Performing platform validation of cluster:', 'Platform Validation', 'Cluster Service'),
                (r'Cluster reference:.*in spec', 'Cluster Reference', 'Cluster Service'),
                
                # Image Operations
                (r'Performing get image for.*image', 'Image Retrieval', 'Image Service'),
                (r'Image information for.*image is', 'Image Info Response', 'Image Service'),
                
                # API Operations
                (r'Relative url for subnet entity get api is', 'Subnet API URL', 'API Helper'),
                (r'Relative url for image entity get api is', 'Image API URL', 'API Helper'),
                (r'Relative url for cluster entity get api is', 'Cluster API URL', 'API Helper'),
                (r'>>GET https://.*subnets/', 'Subnet API Call', 'HTTP Client'),
                (r'>>GET https://.*images/', 'Image API Call', 'HTTP Client'),
                (r'>>GET https://.*clusters/', 'Cluster API Call', 'HTTP Client'),
                (r'>>GET https://.*subnets/[a-f0-9-]+', 'Subnet API Call', 'HTTP Client'),
                (r'>>GET https://.*images/[a-f0-9-]+', 'Image API Call', 'HTTP Client'),
                (r'>>GET https://.*clusters/[a-f0-9-]+', 'Cluster API Call', 'HTTP Client'),
                (r'<< 200 \{"api_version":', 'API Response Success', 'HTTP Client'),
                
                # Ergon Operations
                (r'Updated milestone and response in workstate', 'Milestone Update', 'Ergon Helper'),
                (r'Notifying master for ergon task.*done', 'Task Complete', 'Ergon Service'),
                
                # Generic HTTP Operations
                (r'>>GET https://.*', 'HTTP GET Request', 'HTTP Client'),
                (r'<< 200', 'HTTP Response', 'HTTP Client'),
                
                # Legacy patterns
                (r'Failed to get host details', 'Host Lookup Error', 'VMware Provider'),
                (r'Initiating platform data fetch', 'Platform Data Fetch', 'VMware Client'),
            ],
            'narad': [
                # Core Request Processing
                (r'Request with runID ([a-f0-9-]+)', 'Run Request', 'Narad Worker'),
                (r'handleQueuedTask', 'Task Processing', 'Task Queue'),
                
                # Ergon Task Management
                (r'Setting ergon task id ([a-f0-9-]+) in RUNNING state', 'Task State Update', 'Ergon Utils'),
                (r'Setting ergon task_id \(([a-f0-9-]+)\) milestone as \'RUNNING\'', 'Milestone Update', 'Ergon Utils'),
                (r'Setting ergon task_id \(([a-f0-9-]+)\) milestone as \'SCRIPT_EXECUTED\'', 'Script Milestone', 'Ergon Utils'),
                (r'Setting ergon task_id \(([a-f0-9-]+)\) milestone as \'SUCCESS\'', 'Success Milestone', 'Ergon Utils'),
                
                # Notification Handling
                (r'Notifying with Data', 'Data Notification', 'Notification Handler'),
                (r'notifyHandler', 'Notification Handler', 'Notification Service'),
                (r'notifyView', 'View Notification', 'View Handler'),
                
                # Script Execution
                (r'Script execution completed\. Setting the milestone', 'Script Complete', 'Script Engine'),
                (r'exitstatus bytes string', 'Exit Status', 'Script Engine'),
                
                # Callback Management
                (r'Sending callback to durga with callback body', 'Durga Callback', 'Durga Service'),
                (r'Not sending a callback to durga, return URL empty', 'No Callback', 'Callback Handler'),
                
                # HTTP API Calls
                (r'>>POST http://.*runlog/v2/policy_task', 'Policy Task API', 'Runlog Service'),
                (r'>>POST http://.*runlog/v2/task', 'Task API', 'Runlog Service'),
                (r'>>POST.*runlog.*policy_task.*az_status.*RUNNING', 'Policy Running', 'Runlog Service'),
                (r'>>POST.*runlog.*policy_task.*az_status.*POLICY_EXEC', 'Policy Execution', 'Runlog Service'),
                (r'>>POST.*runlog.*policy_task.*az_status.*SUCCESS', 'Policy Success', 'Runlog Service'),
                (r'>>POST.*runlog.*task.*az_status.*RUNNING', 'Task Running', 'Runlog Service'),
                (r'>>POST.*runlog.*task.*az_status.*SUCCESS', 'Task Success', 'Runlog Service'),
                
                # Task Types
                (r'az_task_type.*CLOUD', 'Cloud Task', 'Cloud Handler'),
                (r'az_task_type.*CALL_WORKFLOW', 'Workflow Task', 'Workflow Handler'),
                (r'task_kind.*PROVISION_NUTANIX', 'Nutanix Provision', 'Provision Handler'),
                (r'task_kind.*CREATE_SERVICE_ELEMENT', 'Service Creation', 'Service Handler'),
                
                # Entity Management
                (r'calm_entity_type.*Substrate', 'Substrate Entity', 'Entity Handler'),
                (r'calm_entity_type.*Service', 'Service Entity', 'Entity Handler'),
                (r'calm_entity_type.*AppProfileInstance', 'App Profile Entity', 'Entity Handler'),
            ],
            
            # Add patterns for other services as needed
            'algalon': [
                (r'In postRequestHandler', 'Post Request Handler', 'Request Handler'),
                (r'In preRequestHandler', 'Pre Request Handler', 'Request Handler'),
                (r'middleware.*func', 'Middleware Processing', 'Context Middleware'),
                (r'logger:algalon', 'Algalon Processing', 'Algalon Service'),
            ],
            'iris': [
                (r'POST /runlog/v2/action -> Executing Request', 'Runlog Action Request', 'Iris API'),
                (r'POST /runlog/v2/task -> Executing Request', 'Runlog Task Request', 'Iris API'),
                (r'populateContextDBConfigInternal', 'DB Config Setup', 'DB Middleware'),
            ],
            'vajra': [
                (r'req headers.*Authorization', 'Auth Headers', 'Vajra Auth'),
                (r'Started with new file request', 'File Request', 'File Handler'),
                (r'worker pool size', 'Worker Pool', 'Worker Manager'),
            ],
            'arjun': [
                (r'arjun.*request', 'Request Processing', 'Arjun Service'),
                (r'arjun.*task', 'Task Processing', 'Arjun Task Manager'),
            ],
            'karan': [
                (r'karan.*request', 'Request Processing', 'Karan Service'),
                (r'karan.*task', 'Task Processing', 'Karan Task Manager'),
            ],
        }
        
        # Process each service's logs
        for service, service_info in self.service_logs.items():
            log_dir = self.nucalm_log_dir if service_info['dir'] == 'nucalm' else self.epsilon_log_dir
            for log_file in service_info['files']:
                log_path = log_dir / log_file
                if not log_path.exists():
                    continue
                    
                print(f"  📄 Processing {service} ({service_info['dir'].upper()}): {log_file}")
                self._process_log_file(log_path, service, patterns.get(service, []))
        
        # Filter events with valid timestamps and sort
        valid_events = []
        for event in self.timeline_events:
            if re.match(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', event['timestamp']):
                valid_events.append(event)
        
        self.timeline_events = valid_events
        self.timeline_events.sort(key=lambda x: x['timestamp'])
        
        # Limit events for UI performance (keep first 300 events for comprehensive view)
        if len(self.timeline_events) > 300:
            print(f"⚠️  Found {len(self.timeline_events)} events, limiting to first 300 for UI performance")
            self.timeline_events = self.timeline_events
        
        print(f"✅ Extracted {len(self.timeline_events)} timeline events")
    
    def _process_log_file(self, log_path, service, patterns):
        """Process a single log file for timeline events"""
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    # Check if line contains the root request ID (most important for cross-service correlation)
                    # Also accept lines with the main cr/pr IDs for completeness
                    rr_id = self.reference_ids.get('rr')
                    cr_id = self.reference_ids.get('cr')
                    pr_id = self.reference_ids.get('pr')
                    
                    # Primary check: root request ID (most reliable for cross-service correlation)
                    has_rr = rr_id and rr_id in line
                    # Secondary check: main request IDs from STYX
                    has_main_ids = (cr_id and cr_id in line) or (pr_id and pr_id in line)
                    
                    if not (has_rr or has_main_ids):
                        continue
                    
                    # Extract timestamp - handle both formats (with and without brackets)
                    timestamp_match = re.search(r'\[(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{3,6})?Z?)\]', line)
                    if not timestamp_match:
                        # Try JOVE format (no brackets)
                        timestamp_match = re.search(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+Z)', line)
                        if not timestamp_match:
                            continue
                    
                    timestamp_str = timestamp_match.group(1)
                    # Normalize timestamp format
                    if 'T' not in timestamp_str:
                        timestamp_str = timestamp_str.replace(' ', 'T')
                    if not timestamp_str.endswith('Z'):
                        timestamp_str += 'Z'
                    
                    # Check against patterns
                    for pattern, operation, target_service in patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Extract additional details
                            details = self._extract_details(line, operation)
                            
                            event = {
                                'timestamp': timestamp_str,
                                'service': service.upper(),
                                'operation': operation,
                                'target_service': target_service,
                                'details': details,
                                'line_num': line_num,
                                'log_file': log_path.name
                            }
                            self.timeline_events.append(event)
                            
                            # Track service interactions
                            self._track_service_interaction(service.upper(), target_service, operation, line)
                            break
                            
        except (IOError, OSError, UnicodeDecodeError) as e:
            print(f"⚠️  Error processing {log_path}: {e}")
    
    def _track_service_interaction(self, source_service, target_service, operation, line):
        """Track service-to-service interactions"""
        if source_service not in self.service_interactions:
            self.service_interactions[source_service] = {
                'calls_to': {},
                'receives_from': {},
                'endpoints': set(),
                'operations': set()
            }
        
        # Track outgoing calls
        if target_service != 'Internal':
            if target_service not in self.service_interactions[source_service]['calls_to']:
                self.service_interactions[source_service]['calls_to'][target_service] = []
            self.service_interactions[source_service]['calls_to'][target_service].append(operation)
        
        # Extract endpoints from log line
        endpoint_match = re.search(r'(/[a-zA-Z0-9_/\-]+)', line)
        if endpoint_match:
            self.service_interactions[source_service]['endpoints'].add(endpoint_match.group(1))
        
        # Track operations
        self.service_interactions[source_service]['operations'].add(operation)
    
    def _extract_details(self, line, _operation):
        """Extract specific details based on operation type"""
        details = ""
        
        if 'ergon_task_id' in line:
            task_match = re.search(r'ergon_task_id[\'"]?:\s*[\'"]?([a-f0-9-]+)', line)
            if task_match:
                details = f"Task ID: {task_match.group(1)}"
        
        if 'worker' in line.lower() and 'hercules' in line:
            worker_match = re.search(r'hercules-\d+-[a-f0-9-]+', line)
            if worker_match:
                details = f"Worker: {worker_match.group(0)}"
        
        if 'image_size_bytes' in line:
            size_match = re.search(r'image_size_bytes[\'"]?:\s*(\d+)', line)
            if size_match:
                size_gb = int(size_match.group(1)) / (1024**3)
                details = f"Image size: {size_gb:.1f}GB"
        
        if 'milestone' in line:
            milestone_match = re.search(r'milestone to (\d+)', line)
            if milestone_match:
                details = f"Milestone: {milestone_match.group(1)}"
        
        return details
    
    def generate_sequence_diagram(self):
        """Generate a Mermaid sequence diagram showing chronological service flow"""
        if not self.timeline_events:
            return ""
        
        # Map services to shorter names for diagram readability
        service_map = {
            'STYX': 'STYX',
            'JOVE': 'NUCALM_JOVE', 
            'HERCULES': 'HERCULES',
            'EPSILON_JOVE': 'EPSILON_JOVE',
            'INDRA': 'INDRA',
            'GOZAFFI': 'GOZAFFI',
            'DURGA': 'DURGA',
            'NARAD': 'NARAD',
            'IRIS': 'IRIS',
            'VAJRA': 'VAJRA',
            'ALGALON': 'ALGALON',
            'ARJUN': 'ARJUN',
            'KARAN': 'KARAN'
        }
        
        diagram = "sequenceDiagram\n"
        
        # Only add actual services as participants (from the service column)
        services_in_timeline = set()
        for event in self.timeline_events:
            service = service_map.get(event['service'], event['service'])
            services_in_timeline.add(service)
        
        # Add service participants to diagram in logical order
        service_order = ['STYX', 'NUCALM_JOVE', 'HERCULES', 'EPSILON_JOVE', 'INDRA', 'GOZAFFI', 'DURGA', 'NARAD', 'IRIS', 'VAJRA', 'ALGALON']
        for service in service_order:
            if service in services_in_timeline:
                diagram += f"    participant {service}\n"
        
        diagram += "\n"
        
        # Track the chronological flow of services
        previous_service = None
        interactions = []
        
        # Process events in chronological order to build actual flow
        for event in self.timeline_events:  # Process all events to capture all services
            current_service = service_map.get(event['service'], event['service'])
            operation = event['operation'] + "..." if len(event['operation']) > 20 else event['operation']
            
            # When service changes, show the interaction
            if previous_service and previous_service != current_service:
                # Add the interaction from previous to current service
                interactions.append({
                    'from': previous_service,
                    'to': current_service,
                    'operation': operation,
                    'details': event.get('details', '')
                })
            
            previous_service = current_service
        
        # Generate the sequence diagram from interactions
        for interaction in interactions:
            from_service = interaction['from']
            to_service = interaction['to']
            operation = interaction['operation']
            
            # Add the request
            diagram += f"    {from_service}->>{to_service}: {operation}\n"
        
        # Post-process to group repetitive patterns (from enhanced del.py)
        lines = diagram.split('\n')
        processed_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # First check for App Request/Response 1/2/3 patterns
            if '->>' in line and ('App Request 1' in line or 'App Response 1' in line):
                # Try to find consecutive App Request/Response patterns
                try:
                    parts = line.split('->>')
                    service_from = parts[0].strip()
                    service_to_op = parts[1].split(':')
                    service_to = service_to_op[0].strip()
                    operation = service_to_op[1].strip() if len(service_to_op) > 1 else ''
                    
                    if 'App Request 1' in operation:
                        # Look for App Request 2 and 3, and corresponding responses
                        request_lines = [line]
                        response_lines = []
                        j = i + 1
                        
                        # Collect App Response 1
                        if j < len(lines) and f'{service_to}->>{service_from}: App Response 1' in lines[j]:
                            response_lines.append(lines[j].strip())
                            j += 1
                        
                        # Collect App Request 2
                        if j < len(lines) and f'{service_from}->>{service_to}: App Request 2' in lines[j]:
                            request_lines.append(lines[j].strip())
                            j += 1
                            
                            # Collect App Response 2
                            if j < len(lines) and f'{service_to}->>{service_from}: App Response 2' in lines[j]:
                                response_lines.append(lines[j].strip())
                                j += 1
                        
                        # Collect App Request 3
                        if j < len(lines) and f'{service_from}->>{service_to}: App Request 3' in lines[j]:
                            request_lines.append(lines[j].strip())
                            j += 1
                            
                            # Collect App Response 3
                            if j < len(lines) and f'{service_to}->>{service_from}: App Response 3' in lines[j]:
                                response_lines.append(lines[j].strip())
                                j += 1
                        
                        # If we found multiple requests/responses, consolidate them
                        if len(request_lines) > 1:
                            if len(request_lines) == 3:
                                processed_lines.append(f"    {service_from}->>{service_to}: App Request 1/2/3")
                            elif len(request_lines) == 2:
                                processed_lines.append(f"    {service_from}->>{service_to}: App Request 1/2")
                            
                            if len(response_lines) > 1:
                                if len(response_lines) == 3:
                                    processed_lines.append(f"    {service_to}->>{service_from}: App Response 1/2/3")
                                elif len(response_lines) == 2:
                                    processed_lines.append(f"    {service_to}->>{service_from}: App Response 1/2")
                            
                            i = j
                            continue
                except:
                    pass
            
            if '->>' in line and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                
                # Check for alternating pattern (A->B followed by B->A)
                if '->>' in next_line:
                    # Extract services and operations from both lines
                    try:
                        # Parse first line: "ServiceA->>ServiceB: Operation"
                        parts1 = line.split('->>')
                        service_a = parts1[0].strip()
                        service_b_op1 = parts1[1].split(':')
                        service_b = service_b_op1[0].strip()
                        operation1 = service_b_op1[1].strip() if len(service_b_op1) > 1 else ''
                        
                        # Parse second line
                        parts2 = next_line.split('->>')
                        service_c = parts2[0].strip()
                        service_d_op2 = parts2[1].split(':')
                        service_d = service_d_op2[0].strip()
                        operation2 = service_d_op2[1].strip() if len(service_d_op2) > 1 else ''
                        
                        # Check if it's an alternating pattern (A->B, B->A)
                        if service_a == service_d and service_b == service_c:
                            # Count how many times this pattern repeats
                            pattern_count = 1
                            j = i + 2
                            
                            while j + 1 < len(lines):
                                line_j = lines[j].strip()
                                line_j1 = lines[j + 1].strip()
                                
                                if (line_j == line and line_j1 == next_line):
                                    pattern_count += 1
                                    j += 2
                                else:
                                    break
                            
                            if pattern_count > 1:
                                # Replace with grouped version
                                processed_lines.append(f"    {service_a}->>{service_b}: {operation1} ({pattern_count} times)")
                                processed_lines.append(f"    {service_b}->>{service_a}: {operation2} ({pattern_count} times)")
                                i = j
                                continue
                    except:
                        pass
            
            processed_lines.append(line)
            i += 1
        
        diagram = '\n'.join(processed_lines)
        return diagram
    
    def calculate_performance_metrics(self):
        """Calculate performance metrics from timeline events"""
        metrics = {
            'total_duration': 0,
            'service_durations': defaultdict(list),
            'bottlenecks': [],
            'phase_durations': {}
        }
        
        if len(self.timeline_events) < 2:
            return metrics
        
        try:
            # Helper function to parse timestamps
            def parse_timestamp(ts_str):
                # Normalize timestamp format
                ts = ts_str.replace('Z', '').replace(' ', 'T')
                # Handle microseconds by truncating to milliseconds if needed
                if '.' in ts:
                    parts = ts.split('.')
                    if len(parts[1]) > 3:
                        ts = parts[0] + '.' + parts[1][:3]
                return datetime.fromisoformat(ts)
            
            # Calculate total duration
            start_time = parse_timestamp(self.timeline_events[0]['timestamp'])
            end_time = parse_timestamp(self.timeline_events[-1]['timestamp'])
            metrics['total_duration'] = (end_time - start_time).total_seconds() * 1000  # ms
            
            # Find bottlenecks (operations taking > 100ms)
            for i in range(len(self.timeline_events) - 1):
                try:
                    current = parse_timestamp(self.timeline_events[i]['timestamp'])
                    next_event = parse_timestamp(self.timeline_events[i + 1]['timestamp'])
                    duration = (next_event - current).total_seconds() * 1000
                    
                    if duration > 100:  # > 100ms
                        metrics['bottlenecks'].append({
                            'operation': self.timeline_events[i]['operation'],
                            'service': self.timeline_events[i]['service'],
                            'duration_ms': round(duration, 1)
                        })
                except ValueError as e:
                    print("⚠️  Timestamp parsing error for event: {}".format(e))
                    continue
                    
        except ValueError as e:
            print("⚠️  Could not calculate performance metrics: {}".format(e))
            
        return metrics
    
    def generate_timeline_analysis(self, app_uuid, nucalm_log_directory, epsilon_log_directory):
        """Generate complete timeline analysis - main method called by analyzer"""
        self.app_uuid = app_uuid
        
        print(f"🚀 Starting timeline generation for app UUID: {app_uuid}")
        print(f"📁 NUCALM log directory: {nucalm_log_directory}")
        print(f"📁 EPSILON log directory: {epsilon_log_directory}")
        
        # Update directories
        self.nucalm_log_dir = Path(nucalm_log_directory)
        self.epsilon_log_dir = Path(epsilon_log_directory) if epsilon_log_directory else None
        
        # Re-discover service logs with updated directories
        self.service_logs = self._discover_service_logs()
        
        # Step 1: Find reference IDs
        if not self.find_reference_ids(app_uuid):
            print("❌ Could not find reference IDs for the given app UUID")
            return {
                'events': [],
                'summary': 'No reference IDs found',
                'sequence_diagram': '',
                'service_counts': {}
            }
        
        # Step 2: Extract timeline events
        self.extract_timeline_events()
        
        if not self.timeline_events:
            print("❌ No timeline events found for the given app UUID")
            return {
                'events': [],
                'summary': 'No timeline events found',
                'sequence_diagram': '',
                'service_counts': {}
            }
        
        # Step 3: Calculate service counts
        service_counts = defaultdict(int)
        for event in self.timeline_events:
            service_counts[event['service']] += 1
        
        # Step 4: Generate sequence diagram
        sequence_diagram = self.generate_sequence_diagram()
        
        # Step 5: Calculate performance metrics
        metrics = self.calculate_performance_metrics()
        
        print("🎉 Timeline generation completed successfully!")
        print(f"📊 Found {len(self.timeline_events)} events across {len(service_counts)} services")
        
        return {
            'events': self.timeline_events,
            'summary': f"Found {len(self.timeline_events)} events across {len(service_counts)} services. Total duration: {metrics['total_duration']:.1f}ms",
            'sequence_diagram': sequence_diagram,
            'service_counts': dict(service_counts),
            'reference_ids': self.reference_ids,
            'performance_metrics': metrics
        }


# Wrapper class to maintain compatibility with existing code
class TimelineGenerator:
    def __init__(self, nucalm_log_dir, epsilon_log_dir=None, logger=None):
        self.generator = AppTimelineGenerator(nucalm_log_dir, epsilon_log_dir, logger)
    
    def generate_timeline_analysis(self, app_uuid, nucalm_log_directory, epsilon_log_directory):
        return self.generator.generate_timeline_analysis(app_uuid, nucalm_log_directory, epsilon_log_directory)