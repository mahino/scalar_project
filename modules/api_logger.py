"""
API Logger Module - Logs all internal and external API requests/responses
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class APILogger:
    def __init__(self, base_dir: str = "api_logs"):
        self.base_dir = Path(base_dir)
        self.internal_dir = self.base_dir / "internal"
        self.external_dir = self.base_dir / "external"
        
        # Create directories if they don't exist
        self.internal_dir.mkdir(parents=True, exist_ok=True)
        self.external_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logger
        self.logger = logging.getLogger('api_logger')
        
    def log_internal_request(self, endpoint: str, method: str, request_data: Dict[Any, Any], 
                           response_data: Dict[Any, Any], status_code: int, 
                           duration_ms: float, client_ip: str = None):
        """Log internal API requests (our Flask endpoints)"""
        timestamp = datetime.now()
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "type": "internal",
            "endpoint": endpoint,
            "method": method.upper(),
            "client_ip": client_ip,
            "request": {
                "data": request_data,
                "headers": {},  # Can be extended to include headers
            },
            "response": {
                "status_code": status_code,
                "data": response_data,
                "duration_ms": duration_ms
            }
        }
        
        # Create filename with timestamp and endpoint
        safe_endpoint = endpoint.replace('/', '_').replace(':', '')
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{safe_endpoint}_{method.lower()}.json"
        filepath = self.internal_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(log_entry, f, indent=2, default=str)
            self.logger.info(f"Logged internal API call: {endpoint} -> {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to log internal API call: {e}")
    
    def log_external_request(self, url: str, method: str, request_data: Optional[Dict[Any, Any]], 
                           response_data: Optional[Dict[Any, Any]], status_code: Optional[int], 
                           duration_ms: float, error: str = None, service_name: str = "unknown"):
        """Log external API requests (to third-party services like Jarvis)"""
        timestamp = datetime.now()
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "type": "external",
            "service": service_name,
            "url": url,
            "method": method.upper(),
            "request": {
                "data": request_data,
                "params": {},  # Can be extended to include query params
            },
            "response": {
                "status_code": status_code,
                "data": response_data,
                "duration_ms": duration_ms,
                "error": error
            }
        }
        
        # Create filename with timestamp and service
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{service_name}_{method.lower()}.json"
        filepath = self.external_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(log_entry, f, indent=2, default=str)
            self.logger.info(f"Logged external API call: {service_name} -> {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to log external API call: {e}")
    
    def log_jarvis_request(self, url: str, method: str, params: Dict[str, Any], 
                          response_data: Optional[Dict[Any, Any]], status_code: Optional[int], 
                          duration_ms: float, error: str = None):
        """Specialized method for logging Jarvis API calls"""
        timestamp = datetime.now()
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "type": "external",
            "service": "jarvis",
            "url": url,
            "method": method.upper(),
            "request": {
                "params": params,
                "headers": {"User-Agent": "Scalar-Project-Dashboard"}
            },
            "response": {
                "status_code": status_code,
                "data": response_data,
                "duration_ms": duration_ms,
                "error": error,
                "success": status_code == 200 if status_code else False
            },
            "metadata": {
                "pool_id": params.get("pool_id", "unknown"),
                "limit": params.get("limit", 25),
                "page": params.get("page", 1)
            }
        }
        
        # Create filename with pool ID for easier identification
        pool_id = params.get("pool_id", "unknown")
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_jarvis_{pool_id}_{method.lower()}.json"
        filepath = self.external_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(log_entry, f, indent=2, default=str)
            self.logger.info(f"Logged Jarvis API call: {pool_id} -> {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to log Jarvis API call: {e}")
    
    def get_recent_logs(self, log_type: str = "all", limit: int = 10):
        """Get recent API logs"""
        logs = []
        
        if log_type in ["all", "internal"]:
            for log_file in sorted(self.internal_dir.glob("*.json"), reverse=True)[:limit]:
                try:
                    with open(log_file, 'r') as f:
                        logs.append(json.load(f))
                except Exception as e:
                    self.logger.error(f"Failed to read log file {log_file}: {e}")
        
        if log_type in ["all", "external"]:
            for log_file in sorted(self.external_dir.glob("*.json"), reverse=True)[:limit]:
                try:
                    with open(log_file, 'r') as f:
                        logs.append(json.load(f))
                except Exception as e:
                    self.logger.error(f"Failed to read log file {log_file}: {e}")
        
        return sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
    
    def cleanup_old_logs(self, days_to_keep: int = 7):
        """Clean up log files older than specified days"""
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        
        for log_dir in [self.internal_dir, self.external_dir]:
            for log_file in log_dir.glob("*.json"):
                try:
                    if log_file.stat().st_mtime < cutoff_time:
                        log_file.unlink()
                        self.logger.info(f"Cleaned up old log file: {log_file}")
                except Exception as e:
                    self.logger.error(f"Failed to cleanup log file {log_file}: {e}")

# Global instance
api_logger = APILogger()
