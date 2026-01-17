"""
Logging Manager Module
Handles all logging configuration and API request/response logging
"""

import os
import logging
import sys
import json
import glob
from datetime import datetime
from typing import Optional, Any


class LoggingManager:
    """Manages application logging and API request/response logging"""
    
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.logs_dir = os.path.join(base_dir, 'logs')
        self.api_logs_dir = os.path.join(base_dir, 'api_logs')
        self.max_api_logs_per_endpoint = 10
        
        # Create directories
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.api_logs_dir, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup application logging configuration"""
        # Create new log file on each restart
        log_filename = os.path.join(
            self.logs_dir, 
            f'payload_scaler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        
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
        self.logger = logging.getLogger('payload_scaler')
        self.logger.info("="*80)
        self.logger.info("PAYLOAD SCALER APPLICATION STARTING")
        self.logger.info("="*80)
        
    def get_logger(self) -> logging.Logger:
        """Get the application logger"""
        return self.logger
        
    def ensure_api_log_dir(self, api_name: str) -> str:
        """Ensure API log directory exists for the given API name"""
        api_dir = os.path.join(self.api_logs_dir, api_name)
        os.makedirs(api_dir, exist_ok=True)
        return api_dir
        
    def manage_api_log_fifo(self, api_dir: str, max_files: int = None) -> None:
        """Manage FIFO for API logs - keep only the most recent files"""
        if max_files is None:
            max_files = self.max_api_logs_per_endpoint
            
        try:
            # Get all JSON files in the directory
            json_files = glob.glob(os.path.join(api_dir, '*.json'))
            
            if len(json_files) > max_files:
                # Sort by modification time (oldest first)
                json_files.sort(key=lambda x: os.path.getmtime(x))
                
                # Remove oldest files
                files_to_remove = json_files[:-max_files]
                for file_path in files_to_remove:
                    try:
                        os.remove(file_path)
                        self.logger.debug(f"Removed old API log file: {file_path}")
                    except OSError as e:
                        self.logger.warning(f"Could not remove old API log file {file_path}: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error managing API log FIFO for {api_dir}: {e}")
            
    def log_api_request_response(
        self, 
        api_name: str, 
        endpoint: str, 
        method: str, 
        request_data: Optional[Any] = None, 
        response_data: Optional[Any] = None, 
        status_code: Optional[int] = None, 
        error: Optional[str] = None
    ) -> None:
        """Log API request and response to structured files"""
        try:
            # Ensure API log directory exists
            api_dir = self.ensure_api_log_dir(api_name)
            
            # Manage FIFO
            self.manage_api_log_fifo(api_dir)
            
            # Create log entry
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
            filename = f"{timestamp}_{method.lower()}_{api_name}.json"
            filepath = os.path.join(api_dir, filename)
            
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
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"API request/response logged: {api_name} {method} {endpoint}")
            
        except Exception as e:
            self.logger.error(f"Error logging API request/response for {api_name}: {e}")
