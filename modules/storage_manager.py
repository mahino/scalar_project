"""
Storage Manager Module
Handles file storage, rules management, and history tracking
"""

import os
import json
import copy
from typing import Dict, List, Any, Optional
from datetime import datetime


class StorageManager:
    """Manages file storage for rules, templates, and history"""
    
    def __init__(self, base_dir: str, logger):
        self.base_dir = base_dir
        self.logger = logger
        
        # Directory structure
        self.rules_dir = os.path.join(base_dir, 'rules')
        self.templates_dir = os.path.join(base_dir, 'templates_store')
        self.history_dir = os.path.join(base_dir, 'history')
        self.api_rules_file = os.path.join(base_dir, 'api_rules.json')
        
        # Create necessary directories
        os.makedirs(self.history_dir, exist_ok=True)
        
        # Supported API types and default values
        self.api_types = ['blueprint', 'app', 'runbook']
        self.default_action_values = [
            "action_create", "action_delete", "action_start", 
            "action_stop", "action_restart"
        ]
        
    def get_rules_path(self, api_type: str) -> str:
        """Get the rules directory path for an API type"""
        return os.path.join(self.rules_dir, api_type)
        
    def load_default_rules(self, api_type: str) -> Dict[str, Any]:
        """Load default rules for an API type"""
        rules_path = self.get_rules_path(api_type)
        default_rules_file = os.path.join(rules_path, 'default_rules.json')
        
        if os.path.exists(default_rules_file):
            try:
                with open(default_rules_file, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                    self.logger.info(f"Loaded default rules for {api_type} from {default_rules_file}")
                    return rules
            except Exception as e:
                self.logger.error(f"Error loading default rules for {api_type}: {e}")
                return {}
        else:
            self.logger.warning(f"No default rules file found for {api_type} at {default_rules_file}")
            return {}
            
    def load_api_rules(self) -> Dict[str, Any]:
        """Load all API rules from storage"""
        if os.path.exists(self.api_rules_file):
            try:
                with open(self.api_rules_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading API rules: {e}")
        return {}
        
    def save_api_rules(self, rules_data: Dict[str, Any]) -> None:
        """Save API rules to storage"""
        try:
            with open(self.api_rules_file, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving API rules: {e}")
            
    def save_api_rule_set(
        self, 
        api_url: str, 
        api_type: str, 
        rules: List[Dict], 
        payload_template: Any = None, 
        scalable_entities: List[str] = None,
        task_execution: str = 'parallel'
    ) -> None:
        """Save a complete rule set for an API"""
        all_rules = self.load_api_rules()
        
        rule_set = {
            'api_type': api_type,
            'rules': rules,
            'task_execution': task_execution,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        if payload_template is not None:
            rule_set['payload_template'] = payload_template
            
        if scalable_entities is not None:
            rule_set['scalable_entities'] = scalable_entities
            
        all_rules[api_url] = rule_set
        self.save_api_rules(all_rules)
        
        # Also save to history
        self.add_to_history(api_url, rule_set, payload_template)
        
    def get_api_rule_set(self, api_url: str) -> Dict[str, Any]:
        """Get rule set for a specific API"""
        all_rules = self.load_api_rules()
        return all_rules.get(api_url, {})
        
    def delete_api_rule_set(self, api_url: str) -> bool:
        """Delete rule set for a specific API"""
        all_rules = self.load_api_rules()
        if api_url in all_rules:
            # Save to history before deletion
            deleted_rule_set = all_rules[api_url]
            deleted_rule_set['deleted_at'] = datetime.now().isoformat()
            self.add_to_history(f"{api_url}_deleted", deleted_rule_set)
            
            del all_rules[api_url]
            self.save_api_rules(all_rules)
            return True
        return False
        
    def load_payload_template(self, api_url: str) -> Any:
        """Load payload template for an API"""
        rule_set = self.get_api_rule_set(api_url)
        return rule_set.get('payload_template')
        
    def get_history_file(self, entity_name: str) -> str:
        """Get history file path for an entity"""
        return os.path.join(self.history_dir, f"{entity_name}_history.json")
        
    def load_entity_history(self, entity_name: str) -> List[Dict]:
        """Load history for an entity"""
        history_file = self.get_history_file(entity_name)
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading history for {entity_name}: {e}")
        return []
        
    def save_entity_history(self, entity_name: str, history: List[Dict]) -> None:
        """Save history for an entity"""
        history_file = self.get_history_file(entity_name)
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving history for {entity_name}: {e}")
            
    def get_response_history_file_path(self, api_url: str) -> str:
        """Get response history file path for an API"""
        return os.path.join(self.history_dir, f"{api_url}_responses.json")
        
    def save_response_history(self, api_url: str, response_payload: Any, entity_counts: Dict[str, int]) -> None:
        """Save response to history with FIFO management"""
        history_file = self.get_response_history_file_path(api_url)
        
        # Load existing history
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading response history for {api_url}: {e}")
                history = []
                
        # Create new entry
        new_entry = {
            "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3],
            "entity_counts": entity_counts,
            "response_payload": response_payload
        }
        
        # Add to beginning of list
        history.insert(0, new_entry)
        
        # Keep only last 5 entries (FIFO)
        history = history[:5]
        
        # Save back to file
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Error saving response history for {api_url}: {e}")
            
    def get_response_history(self, api_url: str) -> List[Dict[str, Any]]:
        """Get response history for an API"""
        history_file = self.get_response_history_file_path(api_url)
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading response history for {api_url}: {e}")
        return []
        
    def add_to_history(self, entity_name: str, rule_data: Dict, payload_template: Any = None) -> None:
        """Add entry to entity history with FIFO management"""
        history = self.load_entity_history(entity_name)
        
        # Create new entry
        new_entry = {
            "timestamp": datetime.now().isoformat(),
            "rules": copy.deepcopy(rule_data.get('rules', [])),
            "api_type": rule_data.get('api_type', 'unknown'),
            "task_execution": rule_data.get('task_execution', 'parallel')
        }
        
        if payload_template is not None:
            new_entry["payload_template"] = copy.deepcopy(payload_template)
            
        # Add to beginning
        history.insert(0, new_entry)
        
        # Keep only last 10 entries
        history = history[:10]
        
        self.save_entity_history(entity_name, history)
        
    def get_history_version(self, entity_name: str, version_index: int) -> Dict:
        """Get specific version from history"""
        history = self.load_entity_history(entity_name)
        if 0 <= version_index < len(history):
            return history[version_index]
        return {}
        
    def restore_from_history(self, entity_name: str, version_index: int) -> bool:
        """Restore entity from history version"""
        history_entry = self.get_history_version(entity_name, version_index)
        if history_entry:
            try:
                # Save current as new rule set
                self.save_api_rule_set(
                    entity_name,
                    history_entry.get('api_type', 'blueprint'),
                    history_entry.get('rules', []),
                    history_entry.get('payload_template'),
                    task_execution=history_entry.get('task_execution', 'parallel')
                )
                return True
            except Exception as e:
                self.logger.error(f"Error restoring {entity_name} from history: {e}")
        return False
