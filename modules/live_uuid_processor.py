"""
Live UUID Processor Module
Handles applying live UUIDs from Nutanix PC to generated payloads
"""

import copy
import json
from typing import Dict, Any


class LiveUuidProcessor:
    """Handles applying live UUIDs to generated payloads"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def apply_live_uuids_to_payload(self, payload: Any, live_uuids: Dict[str, Any]) -> Any:
        """
        Apply live UUIDs to the generated payload.
        
        Args:
            payload: The generated payload
            live_uuids: Dictionary containing live UUIDs from PC
            
        Returns:
            Modified payload with live UUIDs applied
        """
        if not isinstance(payload, dict) or not live_uuids:
            self.logger.info("No payload or live UUIDs provided, skipping UUID application")
            return payload
        
        self.logger.info(f"Applying live UUIDs to payload: {json.dumps(live_uuids, indent=2)}")
        
        # Make a deep copy to avoid modifying the original
        modified_payload = copy.deepcopy(payload)
        
        # Apply project reference if available
        if live_uuids.get('project', {}).get('uuid'):
            project_uuid = live_uuids['project']['uuid']
            self.logger.info(f"Applying project UUID: {project_uuid}")
            if 'metadata' in modified_payload and 'project_reference' in modified_payload['metadata']:
                modified_payload['metadata']['project_reference']['uuid'] = project_uuid
        else:
            self.logger.error("No project UUID provided, skipping project UUID application")
            raise ValueError("No project UUID provided, skipping project UUID application")
        
        # Get resources section
        resources = modified_payload.get('spec', {}).get('resources', {})
        if not resources:
            self.logger.error("No resources provided, skipping UUID application")
            raise ValueError("No resources provided, skipping UUID application")
        
        # Handle runbook-specific resources
        runbook = resources.get('runbook', {})
        if runbook:
            # Apply live UUIDs to runbook tasks if needed
            for task in runbook.get('task_definition_list', []):
                # Apply cluster/environment references to runbook tasks if they have target references
                if live_uuids.get('cluster', {}).get('uuid') and 'target_any_local_reference' in task:
                    if task['target_any_local_reference'].get('kind') == 'cluster':
                        task['target_any_local_reference']['uuid'] = live_uuids['cluster']['uuid']
        
        
        self.logger.info(f"Applying account references: {json.dumps(live_uuids.get('account', {}), indent=2)}")
        # Apply account references
        if live_uuids.get('account', {}).get('pc_uuid'):
            account_uuid = live_uuids['account'].get('pc_uuid')
            account_name = live_uuids['account'].get('name', '')
            self.logger.info(f"Applying account UUID : {account_uuid} (name: {account_name})")
            account_count = 0
            for substrate in resources.get('substrate_definition_list', []):
                if 'create_spec' in substrate and 'resources' in substrate['create_spec']:
                    substrate_resources = substrate['create_spec']['resources']
                    substrate_resources['account_uuid'] = account_uuid
                    account_count += 1
                    self.logger.info(f"Applied account to substrate create_spec {substrate.get('name', 'unnamed')}: -> '{account_uuid}'")
            
            self.logger.info(f"Account UUID applied to {account_count} substrate locations")
        
        # Apply cluster references
        if live_uuids.get('cluster', {}).get('uuid'):
            cluster_uuid = live_uuids['cluster']['uuid']
            cluster_name = live_uuids['cluster'].get('name', '')
            self.logger.info(f"Applying cluster UUID: {cluster_uuid} (name: {cluster_name})")
            
            cluster_count = 0
            # Update substrate definitions
            for substrate in resources.get('substrate_definition_list', []):
                if 'create_spec' in substrate and 'resources' in substrate['create_spec']:
                    substrate_resources = substrate['create_spec']['resources']
                    if 'cluster_reference' in substrate_resources:
                        old_uuid = substrate_resources['cluster_reference'].get('uuid')
                        
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
                        self.logger.info(f"Applied cluster to substrate {substrate.get('name', 'unnamed')}: UUID {old_uuid} -> {cluster_uuid}, Name: {substrate_resources['cluster_reference']['name']}")
                
                # Also check create_spec for cluster references
                if 'create_spec' in substrate:
                    create_spec = substrate['create_spec']
                    if 'cluster_reference' in create_spec:
                        old_uuid = create_spec['cluster_reference'].get('uuid')
                        
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
                        self.logger.info(f"Applied cluster to substrate create_spec {substrate.get('name', 'unnamed')}: UUID {old_uuid} -> {cluster_uuid}, Name: {create_spec['cluster_reference']['name']}")
            
            self.logger.info(f"Cluster UUID applied to {cluster_count} locations")
        else:
            self.logger.info("No cluster UUID provided, skipping cluster UUID application")
            raise ValueError("No cluster UUID provided, skipping cluster UUID application")

        # Apply environment references
        if live_uuids.get('environment', {}).get('uuid'):
            env_uuid = live_uuids['environment']['uuid']
            env_name = live_uuids['environment'].get('name', '')
            self.logger.info(f"Applying environment UUID: {env_uuid} (name: {env_name})")
            
            # Update substrate definitions
            substrate_count = 0
            for substrate in resources.get('substrate_definition_list', []):
                if 'create_spec' in substrate and 'resources' in substrate['create_spec']:
                    substrate_resources = substrate['create_spec']['resources']
                    if 'environment_reference' in substrate_resources:
                        substrate_resources['environment_reference']['uuid'] = env_uuid
                        if env_name:
                            substrate_resources['environment_reference']['name'] = env_name
                        substrate_count += 1
                        self.logger.info(f"Applied environment UUID to substrate: {substrate.get('name', 'unnamed')}")
            
            # Also check if environment needs to be applied to the main payload metadata
            if 'metadata' in modified_payload:
                if 'project_reference' in modified_payload['metadata']:
                    # Some payloads might have environment reference in metadata
                    if 'environment_reference' in modified_payload['metadata']:
                        modified_payload['metadata']['environment_reference']['uuid'] = env_uuid
                        if env_name:
                            modified_payload['metadata']['environment_reference']['name'] = env_name
                        self.logger.info("Applied environment UUID to payload metadata")
            
            self.logger.info(f"Environment UUID applied to {substrate_count} substrates")
        else:
            self.logger.info("No environment UUID provided, skipping environment UUID application")
        # Apply network references
        if live_uuids.get('network', {}).get('uuid'):
            network_uuid = live_uuids['network']['uuid']
            self.logger.info(f"Applying network UUID: {network_uuid}")
            network_name = live_uuids['network'].get('name', '')
            self.logger.info(f"Applying network name: {network_name}")
            # Update substrate NICs
            for substrate in resources.get('substrate_definition_list', []):
                if 'create_spec' in substrate and 'resources' in substrate['create_spec']:
                    substrate_resources = substrate['create_spec']['resources']
                    for nic in substrate_resources.get('nic_list', []):
                        if 'subnet_reference' in nic:
                            nic['subnet_reference']['uuid'] = network_uuid
        else:
            self.logger.info("No network UUID provided, skipping network UUID application")
        
        # Apply subnet references
        if live_uuids.get('subnet', {}).get('uuid'):
            subnet_uuid = live_uuids['subnet']['uuid']
            subnet_name = live_uuids['subnet'].get('name', '')
            self.logger.info(f"Applying subnet UUID: {subnet_uuid}")
            self.logger.info(f"Applying subnet name: {subnet_name}")
            # Update substrate NICs (if different from network)
            for substrate in resources.get('substrate_definition_list', []):
                if 'create_spec' in substrate and 'resources' in substrate['create_spec']:
                    substrate_resources = substrate['create_spec']['resources']
                    for nic in substrate_resources.get('nic_list', []):
                        if 'subnet_reference' in nic and not live_uuids.get('network', {}).get('uuid'):
                            nic['subnet_reference']['uuid'] = subnet_uuid
                            if subnet_name:
                                nic['subnet_reference']['name'] = subnet_name
        else:
            self.logger.info("No subnet UUID provided, skipping subnet UUID application")
        # Apply image references
        if live_uuids.get('image', {}).get('uuid'):
            image_uuid = live_uuids['image']['uuid']
            image_name = live_uuids['image'].get('name', '')
            self.logger.info(f"Applying image UUID: {image_uuid}")
            self.logger.info(f"Applying image name: {image_name}")
            # Update substrate resources
            for substrate in resources.get('substrate_definition_list', []):
                self.logger.info(f"Applying image to substrate: {substrate.get('name', 'unnamed')}")
                if 'create_spec' in substrate and 'resources' in substrate['create_spec']:
                    substrate_resources = substrate['create_spec']['resources']
                    for disk in substrate_resources.get('disk_list', []):
                        self.logger.info(f"Applying image to disk: {disk.get('name', 'unnamed')}")
                        if 'data_source_reference' in disk:
                            self.logger.info(f"Applying image to data_source_reference: {disk['data_source_reference'].get('name', 'unnamed')}")
                            disk['data_source_reference']['uuid'] = image_uuid
                            if image_name:
                                disk['data_source_reference']['name'] = image_name
        else:
            self.logger.info("No image UUID provided, skipping image UUID application")
            raise ValueError("No image UUID provided, skipping image UUID application")
        
        self.logger.info(f"Applying comprehensive UUID mappings for all entity types: {json.dumps(modified_payload, indent=2)}")
        self._apply_comprehensive_uuid_mappings(modified_payload, live_uuids)
        return modified_payload
        
    def _apply_comprehensive_uuid_mappings(self, payload: Dict[str, Any], live_uuids: Dict[str, Any]) -> None:
        """
        Apply comprehensive UUID mappings for all entity types in the payload.
        This handles cross-entity references like package_definition_list and service_definition_list.
        """
        if not isinstance(payload, dict):
            return
        
        self.logger.info("Applying comprehensive UUID mappings for all entity types")
        
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
                self.logger.info(f"Found package_definition UUID: {package_def['uuid']} (name: {package_def.get('name', 'unnamed')})")
        
        # Extract service definition UUIDs  
        for service_def in resources.get('service_definition_list', []):
            if 'uuid' in service_def:
                app_service_definition_uuids.append(service_def['uuid'])
                self.logger.info(f"Found service_definition UUID: {service_def['uuid']} (name: {service_def.get('name', 'unnamed')})")
        
        # Extract substrate definition UUIDs
        for substrate_def in resources.get('substrate_definition_list', []):
            if 'uuid' in substrate_def:
                app_substrate_definition_uuids.append(substrate_def['uuid'])
                self.logger.info(f"Found substrate_definition UUID: {substrate_def['uuid']} (name: {substrate_def.get('name', 'unnamed')})")
        
        # Extract credential definition UUIDs
        for credential_def in resources.get('credential_definition_list', []):
            if 'uuid' in credential_def:
                app_credential_definition_uuids.append(credential_def['uuid'])
                self.logger.info(f"Found credential_definition UUID: {credential_def['uuid']} (name: {credential_def.get('name', 'unnamed')})")
        
        # Extract deployment UUIDs from app_profile_list
        for app_profile in resources.get('app_profile_list', []):
            for deployment in app_profile.get('deployment_create_list', []):
                if 'uuid' in deployment:
                    app_profile_deployment_uuids.append(deployment['uuid'])
                    self.logger.info(f"Found deployment UUID: {deployment['uuid']} (name: {deployment.get('name', 'unnamed')})")
        
        self.logger.info(f"Found {len(app_package_definition_uuids)} package definition UUIDs: {app_package_definition_uuids}")
        self.logger.info(f"Found {len(app_service_definition_uuids)} service definition UUIDs: {app_service_definition_uuids}")
        self.logger.info(f"Found {len(app_substrate_definition_uuids)} substrate definition UUIDs: {app_substrate_definition_uuids}")
        self.logger.info(f"Found {len(app_credential_definition_uuids)} credential definition UUIDs: {app_credential_definition_uuids}")
        self.logger.info(f"Found {len(app_profile_deployment_uuids)} deployment UUIDs: {app_profile_deployment_uuids}")
        