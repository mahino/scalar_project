"""
Blueprint Generator Module
Handles blueprint-specific generation and hardcoded rules
"""

import copy
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime


class BlueprintGenerator:
    """Handles blueprint-specific generation logic and hardcoded rules"""
    
    def __init__(self, logger):
        self.logger = logger
        
    def apply_hardcoded_scaling_rules(self, data: Any) -> Any:
        """
        Apply hardcoded scaling rules for blueprint generation.
        
        User Inputs: Services, App Profiles, Credentials
        Hardcoded Rules:
        - Packages = App Profiles × Services (one package per deployment)
        - Deployments per Profile = Services
        - Substrates = App Profiles × Services
        """
        if not isinstance(data, dict) or 'spec' not in data:
            return data
            
        resources = data.get('spec', {}).get('resources', {})
        if not resources:
            return data
            
        # Get current counts
        service_count = len(resources.get('service_definition_list', []))
        app_profile_list = resources.get('app_profile_list', [])
        app_profile_count = len(app_profile_list)
        
        if service_count == 0 or app_profile_count == 0:
            return data
            
        self.logger.info(f"HARDCODED RULES: Services={service_count}, App Profiles={app_profile_count}")
        
        # RULE 1: Each app profile should have exactly 'service_count' deployments
        for app_profile in app_profile_list:
            current_deployments = app_profile.get('deployment_create_list', [])
            current_deployment_count = len(current_deployments)
            
            if current_deployment_count > service_count:
                # Remove excess deployments
                app_profile['deployment_create_list'] = current_deployments[:service_count]
                
        # RULE 2: Packages = App Profiles × Services (same as substrates)
        expected_package_count = app_profile_count * service_count
        self.logger.info(f"RULE 2: Setting Packages = App Profiles × Services ({app_profile_count} × {service_count} = {expected_package_count})")
        package_list = resources.get('package_definition_list', [])
        current_package_count = len(package_list)
        
        if current_package_count > expected_package_count:
            # Remove excess packages
            resources['package_definition_list'] = package_list[:expected_package_count]
            
        elif current_package_count < expected_package_count:
            # Add more packages
            if package_list:
                template_package = copy.deepcopy(package_list[0])
                service_list = resources.get('service_definition_list', [])
                service_uuids = [s.get('uuid') for s in service_list if s.get('uuid')]
                
                for i in range(expected_package_count - current_package_count):
                    new_package = copy.deepcopy(template_package)
                    new_package['uuid'] = str(uuid.uuid4())
                    
                    # Calculate which service this package should point to (cycling)
                    global_package_index = current_package_count + i
                    service_index = global_package_index % service_count
                    new_package['name'] = f"Package{global_package_index + 1}"
                    
                    # Update service_local_reference_list to point to the correct service
                    if service_uuids and service_index < len(service_uuids):
                        target_service_uuid = service_uuids[service_index]
                        if 'service_local_reference_list' in new_package:
                            for ref in new_package['service_local_reference_list']:
                                if ref.get('kind') == 'app_service':
                                    ref['uuid'] = target_service_uuid
                        self.logger.info(f"Package{global_package_index + 1} -> Service {service_index + 1} (UUID: {target_service_uuid})")
                    
                    package_list.append(new_package)
                    
        # RULE 3: Substrates = App Profiles × Services
        expected_substrate_count = app_profile_count * service_count
        self.logger.info(f"RULE 3: Setting Substrates = App Profiles × Services ({app_profile_count} × {service_count} = {expected_substrate_count})")
        
        substrate_list = resources.get('substrate_definition_list', [])
        current_substrate_count = len(substrate_list)
        
        if current_substrate_count > expected_substrate_count:
            # Remove excess substrates
            resources['substrate_definition_list'] = substrate_list[:expected_substrate_count]
            
        elif current_substrate_count < expected_substrate_count:
            # Add more substrates
            if substrate_list:
                template_substrate = copy.deepcopy(substrate_list[0])
                for i in range(expected_substrate_count - current_substrate_count):
                    new_substrate = copy.deepcopy(template_substrate)
                    new_substrate['uuid'] = str(uuid.uuid4())
                    new_substrate['name'] = f"VM1_{current_substrate_count + i + 1}"
                    substrate_list.append(new_substrate)
                    
        self.logger.info(f"HARDCODED RULES APPLIED - Final counts: Services={len(resources.get('service_definition_list', []))}, App Profiles={len(resources.get('app_profile_list', []))}, Packages={len(resources.get('package_definition_list', []))}, Substrates={len(resources.get('substrate_definition_list', []))}, Credentials={len(resources.get('credential_definition_list', []))}")
        return data
        
    def fix_blueprint_deployment_references(self, data: Any) -> Any:
        """
        Fix blueprint deployment references to ensure proper UUID mapping.
        This function ensures:
        1. Apply hardcoded scaling rules first
        2. Each deployment references a unique package and substrate
        3. Package runbook tasks reference their own package UUID
        4. Service action tasks reference their own service UUID
        5. All deployment UUIDs are added to client_attrs with grid positioning
        """
        self.logger.info("DEBUG: fix_blueprint_deployment_references called")
        
        # STEP 1: Apply hardcoded scaling rules
        data = self.apply_hardcoded_scaling_rules(data)
        
        if not isinstance(data, dict) or 'spec' not in data:
            self.logger.info("DEBUG: No spec found in data, returning unchanged")
            return data
            
        resources = data.get('spec', {}).get('resources', {})
        if not resources:
            self.logger.info("DEBUG: No resources found, returning unchanged")
            return data
            
        # STEP 2: Continue with UUID mapping (hardcoded rules already applied)
        service_count = len(resources.get('service_definition_list', []))
        app_profile_list = resources.get('app_profile_list', [])
        app_profile_count = len(app_profile_list)
        
        self.logger.info(f"DEBUG: After hardcoded rules - Service count: {service_count}, App profile count: {app_profile_count}")
        
        # Get all entity UUIDs in order
        substrate_uuids = [s.get('uuid') for s in resources.get('substrate_definition_list', []) if s.get('uuid')]
        package_uuids = [p.get('uuid') for p in resources.get('package_definition_list', []) if p.get('uuid')]
        service_uuids = [s.get('uuid') for s in resources.get('service_definition_list', []) if s.get('uuid')]
        
        self.logger.info(f"DEBUG: fix_blueprint_deployment_references - substrate_uuids: {substrate_uuids}")
        self.logger.info(f"DEBUG: fix_blueprint_deployment_references - package_uuids: {package_uuids}")
        self.logger.info(f"DEBUG: fix_blueprint_deployment_references - service_uuids: {service_uuids}")
        
        # Debug: Check current deployment references BEFORE fixing
        deployment_index = 0
        for profile_idx, app_profile in enumerate(app_profile_list):
            deployments = app_profile.get('deployment_create_list', [])
            self.logger.info(f"DEBUG: Profile {profile_idx + 1} has {len(deployments)} deployments")
            
            for dep_idx, deployment in enumerate(deployments):
                current_substrate_ref = deployment.get('substrate_local_reference', {}).get('uuid', 'None')
                current_package_refs = [ref.get('uuid', 'None') for ref in deployment.get('package_local_reference_list', [])]
                self.logger.info(f"DEBUG: BEFORE - Deployment {deployment_index + 1}: substrate={current_substrate_ref}, packages={current_package_refs}")
                deployment_index += 1
                
        # Fix deployment references (distribute entities across deployments)
        deployment_index = 0
        for profile_idx, app_profile in enumerate(app_profile_list):
            deployments = app_profile.get('deployment_create_list', [])
            
            for dep_idx, deployment in enumerate(deployments):
                # Each deployment gets a unique substrate and package
                if deployment_index < len(substrate_uuids):
                    deployment['substrate_local_reference'] = {
                        'kind': 'app_substrate',
                        'uuid': substrate_uuids[deployment_index]
                    }
                    
                if deployment_index < len(package_uuids):
                    deployment['package_local_reference_list'] = [{
                        'kind': 'app_package',
                        'uuid': package_uuids[deployment_index]
                    }]
                    
                self.logger.info(f"DEBUG: AFTER - Deployment {deployment_index + 1}: substrate={substrate_uuids[deployment_index] if deployment_index < len(substrate_uuids) else 'None'}, package={package_uuids[deployment_index] if deployment_index < len(package_uuids) else 'None'}")
                deployment_index += 1
                
        # Fix package-to-service references (distribute packages across services)
        if service_uuids and package_uuids:
            package_list = resources.get('package_definition_list', [])
            self.logger.info(f"DEBUG: Total packages in package_definition_list: {len(package_list)}")
            self.logger.info(f"DEBUG: Expected package_uuids count: {len(package_uuids)}")
            
            for i, package in enumerate(package_list):
                if i < len(service_uuids):
                    # Direct 1:1 mapping for first N packages
                    target_service_uuid = service_uuids[i]
                else:
                    # Round-robin for remaining packages
                    target_service_uuid = service_uuids[i % len(service_uuids)]
                    
                # Update service_local_reference_list
                if 'service_local_reference_list' in package:
                    for ref in package['service_local_reference_list']:
                        if ref.get('kind') == 'app_service':
                            ref['uuid'] = target_service_uuid
                            
                self.logger.info(f"DEBUG: Package {i + 1} -> Service {(i % len(service_uuids)) + 1} (UUID: {target_service_uuid})")
                
        # Add all deployment UUIDs to client_attrs with grid positioning
        # Only update client_attrs if it doesn't exist or is empty
        if 'client_attrs' not in resources or not resources['client_attrs']:
            resources['client_attrs'] = {}
            deployment_count = 0
            
            for app_profile in app_profile_list:
                for deployment in app_profile.get('deployment_create_list', []):
                    deployment_uuid = deployment.get('uuid')
                    if deployment_uuid:
                        # Calculate grid position (10 deployments per row)
                        # row = deployment_count // 10
                        # col = deployment_count % 10
                        x_pos = deployment_count * 120  # 10, 20, 30, 40...
                        y_pos = int(deployment_count/10) * 120  # 10 for first row, 20 for second row...
                        
                        resources['client_attrs'][deployment_uuid] = {
                            "x": x_pos,
                            "y": y_pos
                        }
                        self.logger.info(f"DEBUG: Added deployment {deployment_count} UUID {deployment_uuid} to client_attrs at position ({x_pos}, {y_pos})")
                        deployment_count += 1
        else:
            self.logger.info("DEBUG: client_attrs already exists, skipping regeneration")
                    
        self.logger.info("DEBUG: fix_blueprint_deployment_references completed")
        return data
        
    def generate_blueprint_payload(self, services_count: int, app_profiles_count: int, blueprint_name: str = None) -> Dict[str, Any]:
        """Generate a complete blueprint payload from scratch"""
        self.logger.info(f"Generating blueprint with {services_count} services and {app_profiles_count} app profiles")
        
        # Set default blueprint name if not provided
        if not blueprint_name:
            blueprint_name = f"st_bp_gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Generate UUIDs
        blueprint_uuid = str(uuid.uuid4())
        credential_uuid = str(uuid.uuid4())
        
        # Calculate total entities needed
        total_packages = app_profiles_count * services_count
        total_substrates = app_profiles_count * services_count
        total_deployments = app_profiles_count * services_count
        
        # Generate UUIDs for all entities
        service_uuids = [str(uuid.uuid4()) for _ in range(services_count)]
        substrate_uuids = [str(uuid.uuid4()) for _ in range(total_substrates)]
        package_uuids = [str(uuid.uuid4()) for _ in range(total_packages)]
        deployment_uuids = [str(uuid.uuid4()) for _ in range(total_deployments)]
        app_profile_uuids = [str(uuid.uuid4()) for _ in range(app_profiles_count)]
        
        self.logger.info(f"Generated UUIDs - Services: {len(service_uuids)}, Substrates: {len(substrate_uuids)}, Packages: {len(package_uuids)}, Deployments: {len(deployment_uuids)}, Profiles: {len(app_profile_uuids)}")
        
        # Create base blueprint structure
        blueprint = {
            "api_version": "3.0",
            "metadata": {
                "kind": "blueprint",
                "categories": {},
                "project_reference": {
                    "kind": "project",
                    "uuid": ""
                },
                "uuid": blueprint_uuid
            },
            "spec": {
                "resources": {
                    "service_definition_list": [],
                    "credential_definition_list": [
                        {
                            "name": "admin",
                            "type": "PASSWORD",
                            "cred_class": "static",
                            "username": "root",
                            "secret": {
                                "attrs": {
                                    "is_secret_modified": True
                                },
                                "value": "nutanix/4u"
                            },
                            "uuid": credential_uuid
                        }
                    ],
                    "substrate_definition_list": [],
                    "default_credential_local_reference": {
                        "kind": "app_credential",
                        "uuid": credential_uuid,
                        "name": "default_credential"
                    },
                    "published_service_definition_list": [],
                    "package_definition_list": [],
                    "app_profile_list": [],
                    "client_attrs": {},
                    "type": "USER"
                },
                "name": blueprint_name
            }
        }
        
        # Create services
        self.logger.info(f"Creating {services_count} services...")
        for i in range(services_count):
            service = self.create_service_definition(i + 1, service_uuids[i])
            blueprint["spec"]["resources"]["service_definition_list"].append(service)
            self.logger.info(f"Successfully created service: {service.get('name')}")
            
        # Create substrates
        self.logger.info(f"Creating {total_substrates} substrates...")
        substrate_index = 0
        for profile_idx in range(app_profiles_count):
            for service_idx in range(services_count):
                try:
                    self.logger.info(f"Creating substrate {substrate_index+1}/{total_substrates} (profile {profile_idx+1}, service {service_idx+1})")
                    if substrate_index >= len(substrate_uuids):
                        raise IndexError(f"Substrate index {substrate_index} out of range. Available UUIDs: {len(substrate_uuids)}")
                    
                    substrate = self.create_substrate_definition(substrate_index, substrate_uuids[substrate_index], credential_uuid)
                    blueprint["spec"]["resources"]["substrate_definition_list"].append(substrate)
                    self.logger.info(f"Successfully created substrate: {substrate.get('name')}")
                    substrate_index += 1
                except Exception as e:
                    self.logger.error(f"Error creating substrate {substrate_index+1}: {str(e)}")
                    raise
                    
        # Create packages
        self.logger.info(f"Creating {total_packages} packages...")
        package_index = 0
        for profile_idx in range(app_profiles_count):
            for service_idx in range(services_count):
                try:
                    self.logger.info(f"Creating package {package_index+1}/{total_packages} (profile {profile_idx+1}, service {service_idx+1})")
                    if package_index >= len(package_uuids):
                        raise IndexError(f"Package index {package_index} out of range. Available UUIDs: {len(package_uuids)}")
                    if service_idx >= len(service_uuids):
                        raise IndexError(f"Service index {service_idx} out of range. Available UUIDs: {len(service_uuids)}")
                    
                    # Each package references exactly ONE service (1:1 mapping)
                    package = self.create_package_definition(package_index + 1, package_uuids[package_index], service_uuids[service_idx])
                    blueprint["spec"]["resources"]["package_definition_list"].append(package)
                    self.logger.info(f"Successfully created package: {package.get('name')} -> Service UUID: {service_uuids[service_idx]}")
                    package_index += 1
                except Exception as e:
                    self.logger.error(f"Error creating package {package_index+1}: {str(e)}")
                    raise
                    
        # Create app profiles with deployments
        self.logger.info(f"Creating {app_profiles_count} app profiles...")
        deployment_index = 0
        for profile_idx in range(app_profiles_count):
            try:
                profile_name = "Default" if profile_idx == 0 else f"Profile {profile_idx + 1}"
                
                # Create deployments for this profile
                deployments = []
                for service_idx in range(services_count):
                    if deployment_index >= len(deployment_uuids):
                        raise IndexError(f"Deployment index {deployment_index} out of range. Available UUIDs: {len(deployment_uuids)}")
                    if deployment_index >= len(substrate_uuids):
                        raise IndexError(f"Substrate index {deployment_index} out of range for deployment. Available UUIDs: {len(substrate_uuids)}")
                    if deployment_index >= len(package_uuids):
                        raise IndexError(f"Package index {deployment_index} out of range for deployment. Available UUIDs: {len(package_uuids)}")
                        
                    deployment = self.create_deployment_definition(
                        deployment_index + 1,
                        deployment_uuids[deployment_index],
                        substrate_uuids[deployment_index],
                        package_uuids[deployment_index]
                    )
                    deployments.append(deployment)
                    self.logger.info(f"Created deployment {deployment_index + 1} for profile {profile_idx + 1}")
                    deployment_index += 1
                    
                # Create app profile
                app_profile = self.create_app_profile_definition(profile_name, app_profile_uuids[profile_idx], deployments)
                blueprint["spec"]["resources"]["app_profile_list"].append(app_profile)
                self.logger.info(f"Successfully created app profile: {profile_name}")
                
            except Exception as e:
                self.logger.error(f"Error creating app profile {profile_idx+1}: {str(e)}")
                raise
                
        # Add client_attrs for deployments (grid positioning)
        client_attrs = {}
        for i, deployment_uuid in enumerate(deployment_uuids):
            # Calculate grid position (10 deployments per row)
            row = i // 10
            col = i % 10
            x_pos = (col + 1) * 10  # 10, 20, 30, 40...
            y_pos = (row + 1) * 10  # 10 for first row, 20 for second row...
            
            client_attrs[deployment_uuid] = {
                "x": x_pos,
                "y": y_pos
            }
            
        blueprint["spec"]["resources"]["client_attrs"] = client_attrs
        
        self.logger.info(f"Blueprint generation completed successfully!")
        self.logger.info(f"Final counts - Services: {len(blueprint['spec']['resources']['service_definition_list'])}, Substrates: {len(blueprint['spec']['resources']['substrate_definition_list'])}, Packages: {len(blueprint['spec']['resources']['package_definition_list'])}, App Profiles: {len(blueprint['spec']['resources']['app_profile_list'])}")
        
        return blueprint
        
    def create_service_definition(self, index: int, service_uuid: str) -> Dict[str, Any]:
        """Create a service definition with all required actions"""
        try:
            self.logger.info(f"Creating service definition: index={index}, uuid={service_uuid}")
            actions = []
            action_names = ["action_create", "action_delete", "action_start", "action_stop", "action_restart"]
            self.logger.info(f"Will create {len(action_names)} actions for service {index}")
        except Exception as e:
            self.logger.error(f"Error in create_service_definition: index={index}, error={str(e)}")
            raise
        
        for action_name in action_names:
            runbook_uuid = str(uuid.uuid4())
            task_uuid = str(uuid.uuid4())
            action_uuid = str(uuid.uuid4())
            
            action = {
                "name": action_name,
                "runbook": {
                    "name": f"{action_name}_{index}_runbook",
                    "variable_list": [],
                    "main_task_local_reference": {
                        "kind": "app_task",
                        "uuid": task_uuid
                    },
                    "task_definition_list": [
                        {
                            "name": f"{action_name}_{index}_dag",
                            "target_any_local_reference": {
                                "kind": "app_service",
                                "uuid": service_uuid
                            },
                            "variable_list": [],
                            "child_tasks_local_reference_list": [],
                            "type": "DAG",
                            "attrs": {
                                "edges": []
                            },
                            "uuid": task_uuid
                        }
                    ],
                    "uuid": runbook_uuid
                },
                "type": "system",
                "uuid": action_uuid
            }
            actions.append(action)
        
        return {
            "name": f"Service{index}",
            "depends_on_list": [],
            "variable_list": [],
            "port_list": [],
            "action_list": actions,
            "uuid": service_uuid
        }
        
    def create_substrate_definition(self, index: int, substrate_uuid: str, credential_uuid: str) -> Dict[str, Any]:
        """Create a substrate definition"""
        try:
            vm_names = ["VM1", "VM2", "VM1_3", "VM2_4", "VM5", "VM6", "VM7", "VM8", "VM9", "VM10"]  # Extended list
            vm_name = vm_names[index] if index < len(vm_names) else f"VM{index + 1}"
            self.logger.info(f"Creating substrate definition: index={index}, name={vm_name}, uuid={substrate_uuid}")
        except Exception as e:
            self.logger.error(f"Error in create_substrate_definition: index={index}, error={str(e)}")
            raise
        
        return {
            "variable_list": [],
            "type": "AHV_VM",
            "os_type": "Linux",
            "action_list": [],
            "create_spec": {
                "name": "vm-@@{calm_array_index}@@-@@{calm_time}@@",
                "resources": {
                    "disk_list": [
                        {
                            "data_source_reference": {
                                "kind": "image",
                                "name": "",
                                "uuid": ""
                            },
                            "device_properties": {
                                "device_type": "DISK",
                                "disk_address": {
                                    "device_index": 0,
                                    "adapter_type": "SCSI"
                                }
                            },
                            "disk_size_mib": 20480
                        }
                    ],
                    "memory_size_mib": 1024,
                    "num_sockets": 1,
                    "num_vcpus_per_socket": 1,
                    "account_uuid": "",
                    "boot_config": {
                        "boot_device": {
                            "disk_address": {
                                "device_index": 0,
                                "adapter_type": "SCSI"
                            }
                        },
                        "boot_type": "LEGACY"
                    },
                    "gpu_list": [],
                    "nic_list": [
                        {
                            "subnet_reference": {
                                "uuid": "",
                                "name": ""
                            }
                        }
                    ],
                    "power_state": "ON"
                },
                "categories": {},
                "cluster_reference": {
                    "name": "",
                    "uuid": ""
                }
            },
            "readiness_probe": {
                "disable_readiness_probe": True,
                "address": "@@{platform.status.resources.nic_list[0].ip_endpoint_list[0].ip}@@",
                "login_credential_local_reference": {
                    "kind": "app_credential",
                    "uuid": credential_uuid
                }
            },
            "name": vm_name,
            "uuid": substrate_uuid
        }
        
    def create_package_definition(self, index: int, package_uuid: str, service_uuid: str) -> Dict[str, Any]:
        """Create a package definition with correct service UUID mapping"""
        install_runbook_uuid = str(uuid.uuid4())
        install_task_uuid = str(uuid.uuid4())
        uninstall_runbook_uuid = str(uuid.uuid4())
        uninstall_task_uuid = str(uuid.uuid4())
        
        return {
            "type": "DEB",
            "variable_list": [],
            "options": {
                "install_runbook": {
                    "name": f"install_{index}_runbook",
                    "variable_list": [],
                    "main_task_local_reference": {
                        "kind": "app_task",
                        "uuid": install_task_uuid
                    },
                    "task_definition_list": [
                        {
                            "name": f"install_{index}_dag",
                            "target_any_local_reference": {
                                "kind": "app_package",
                                "uuid": package_uuid
                            },
                            "variable_list": [],
                            "child_tasks_local_reference_list": [],
                            "type": "DAG",
                            "attrs": {
                                "edges": []
                            },
                            "uuid": install_task_uuid
                        }
                    ],
                    "uuid": install_runbook_uuid
                },
                "uninstall_runbook": {
                    "name": f"uninstall_{index}_runbook",
                    "variable_list": [],
                    "main_task_local_reference": {
                        "kind": "app_task",
                        "uuid": uninstall_task_uuid
                    },
                    "task_definition_list": [
                        {
                            "name": f"uninstall_{index}_dag",
                            "target_any_local_reference": {
                                "kind": "app_package",
                                "uuid": package_uuid
                            },
                            "variable_list": [],
                            "child_tasks_local_reference_list": [],
                            "type": "DAG",
                            "attrs": {
                                "edges": []
                            },
                            "uuid": uninstall_task_uuid
                        }
                    ],
                    "uuid": uninstall_runbook_uuid
                }
            },
            "service_local_reference_list": [
                {
                    "kind": "app_service",
                    "uuid": service_uuid
                }
            ],
            "name": f"Package{index}",
            "uuid": package_uuid
        }
        
    def create_deployment_definition(self, index: int, deployment_uuid: str, substrate_uuid: str, package_uuid: str) -> Dict[str, Any]:
        """Create a deployment definition"""
        return {
            "variable_list": [],
            "action_list": [],
            "min_replicas": "1",
            "name": f"deployment_{index}",
            "max_replicas": "1",
            "substrate_local_reference": {
                "kind": "app_substrate",
                "uuid": substrate_uuid
            },
            "default_replicas": "1",
            "type": "GREENFIELD",
            "package_local_reference_list": [
                {
                    "kind": "app_package",
                    "uuid": package_uuid
                }
            ],
            "uuid": deployment_uuid
        }
        
    def create_app_profile_definition(self, name: str, profile_uuid: str, deployments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create an app profile definition"""
        return {
            "name": name,
            "action_list": [],
            "variable_list": [],
            "deployment_create_list": deployments,
            "environment_reference_list": [],
            "uuid": profile_uuid
        }
