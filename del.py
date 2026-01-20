#!/usr/bin/env python3
"""
App-Create Timeline Generator
Generates a complete timeline analysis for any application UUID by analyzing STYX, JOVE, and HERCULES logs.

Usage: python3 generate_app_timeline.py <app_uuid> [log_directory]
"""

import sys
import os
import re
import json
from datetime import datetime
from collections import defaultdict
from pathlib import Path

class AppTimelineGenerator:
    def __init__(self, log_directory="/home/nutanix/log_analyze/nucalm_logs/log"):
        self.log_directory = Path(log_directory)
        self.app_uuid = None
        self.reference_ids = {}
        self.timeline_events = []
        self.service_logs = {
            'styx': ['styx.log', 'styx.log.1', 'styx.log.2'],
            'jove': ['jove.log'],
            'hercules': ['hercules.log']
        }
        
    def find_reference_ids(self, app_uuid):
        """Find all reference IDs associated with the app UUID"""
        print(f"🔍 Searching for reference IDs for app UUID: {app_uuid}")
        
        # Search in STYX logs for APP-CREATE entries
        for log_file in self.service_logs['styx']:
            log_path = self.log_directory / log_file
            if not log_path.exists():
                continue
                
            with open(log_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
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
        
        # Define patterns for different services
        patterns = {
            'styx': [
                (r'APP-CREATE-START', 'APP-CREATE-START', 'Apps API'),
                (r'APP-CREATE-END', 'APP-CREATE-END', 'Apps API'),
                (r'iamv2_interface.*GET request', 'Auth Request', 'IAMv2 Service'),
                (r'username dump:', 'Auth Complete', 'Internal'),
                (r'Fetching project by name:', 'Project Lookup', 'App Blueprint Helper'),
                (r'Calling out bp launch', 'Blueprint Launch', 'Blueprint Launch API'),
                (r'hercules_interface.*scaleout mode', 'Hercules Init', 'Hercules Service'),
                (r'jove_interface.*session created', 'Jove Session', 'Jove Service'),
                (r'jove_interface.*Request-', 'Jove Request', 'Jove Service'),
                (r'jove_interface.*Response-', 'Jove Response', 'Jove Service'),
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
            ],
            'hercules': [
                (r'Creating stub for Ergon', 'Ergon Setup', 'Ergon Service'),
                (r'Updated wal and workstate milestone', 'Milestone Update', 'Ergon Helper'),
                (r'Policy feature is enabled', 'Policy Check', 'Policy Helper'),
                (r'Making api call to fetch size', 'Quota Calculation', 'Quota Helper'),
                (r'Request-.*indra/sync/ImageInfo', 'Image Info Request', 'Indra Service'),
                (r'Response-.*image_size_bytes', 'Image Info Response', 'Indra Service'),
                (r'Policy config ips', 'Policy Config', 'Vidura Interface'),
                (r'plum request body', 'Policy Request', 'Policy Engine'),
                (r'SUCCESS.*APPROVED', 'Policy Response', 'Policy Engine'),
                (r'Cloning the BP', 'Blueprint Clone', 'Hercules Helper'),
            ]
        }
        
        # Process each service's logs
        for service, log_files in self.service_logs.items():
            for log_file in log_files:
                log_path = self.log_directory / log_file
                if not log_path.exists():
                    continue
                    
                print(f"  📄 Processing {service}: {log_file}")
                self._process_log_file(log_path, service, patterns.get(service, []))
        
        # Filter events with valid timestamps and sort
        valid_events = []
        for event in self.timeline_events:
            if re.match(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', event['timestamp']):
                valid_events.append(event)
        
        self.timeline_events = valid_events
        self.timeline_events.sort(key=lambda x: x['timestamp'])
        
        # Limit to most relevant events (first 100 to avoid overwhelming output)
        if len(self.timeline_events) > 100:
            print(f"⚠️  Found {len(self.timeline_events)} events, limiting to first 100 for readability")
            self.timeline_events = self.timeline_events[:100]
        
        print(f"✅ Extracted {len(self.timeline_events)} timeline events")
    
    def _process_log_file(self, log_path, service, patterns):
        """Process a single log file for timeline events"""
        try:
            with open(log_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    # Check if line contains any of our reference IDs (only cr, pr, rr)
                    ref_ids_to_check = [self.reference_ids.get(key) for key in ['cr', 'pr', 'rr'] if self.reference_ids.get(key)]
                    if not any(ref_id in line for ref_id in ref_ids_to_check):
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
                            break
                            
        except Exception as e:
            print(f"⚠️  Error processing {log_path}: {e}")
    
    def _extract_details(self, line, operation):
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
                    print(f"⚠️  Timestamp parsing error for event {i}: {e}")
                    continue
                    
        except ValueError as e:
            print(f"⚠️  Could not calculate performance metrics: {e}")
            
        return metrics
    
    def generate_markdown_report(self, output_file=None):
        """Generate the complete markdown timeline report"""
        if not output_file:
            output_file = f"app_timeline_{self.app_uuid[:8]}.md"
        
        print(f"📝 Generating markdown report: {output_file}")
        
        # Calculate metrics
        metrics = self.calculate_performance_metrics()
        
        # Find app name and blueprint info
        app_name = "Unknown"
        blueprint_name = "Unknown"
        blueprint_uuid = self.reference_ids.get('blueprint_uuid', 'Unknown')
        
        for event in self.timeline_events:
            if 'APP-CREATE-END' in event['operation'] and '::' in event.get('details', ''):
                app_name = event['details'].split('::')[-1] if '::' in event['details'] else app_name
        
        # Generate report content
        content = f"""# Complete App-Create Flow Timeline
**Generated for App UUID:** {self.app_uuid}  
**App Name:** {app_name}  
**Blueprint UUID:** {blueprint_uuid}  
**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  

## Reference IDs
- **Root Request (rr):** `{self.reference_ids.get('rr', 'Not found')}`
- **Parent Request (pr):** `{self.reference_ids.get('pr', 'Not found')}` 
- **Client Request (cr):** `{self.reference_ids.get('cr', 'Not found')}`

---

## 🔄 COMPLETE FLOW TIMELINE

| Time | Service | Operation | Target Service | Details |
|------|---------|-----------|----------------|---------|
"""
        
        # Add timeline events
        for event in self.timeline_events:
            time_str = event['timestamp'][11:23]  # Extract HH:MM:SS.mmm
            content += f"| **{time_str}** | **{event['service']}** | {event['operation']} | **{event['target_service']}** | {event['details']} |\n"
        
        # Add performance analysis
        content += f"""
---

## 📊 PERFORMANCE ANALYSIS

### Overall Metrics
- **Total Flow Duration:** {metrics['total_duration']:.1f}ms
- **Number of Operations:** {len(self.timeline_events)}
- **Services Involved:** {len(set(e['service'] for e in self.timeline_events))}

### Bottlenecks Identified
"""
        
        if metrics['bottlenecks']:
            for bottleneck in metrics['bottlenecks']:
                content += f"- **{bottleneck['service']}** - {bottleneck['operation']}: {bottleneck['duration_ms']}ms ⚠️\n"
        else:
            content += "- No significant bottlenecks detected (all operations < 100ms) ✅\n"
        
        content += f"""
### Service Performance
"""
        
        service_counts = defaultdict(int)
        for event in self.timeline_events:
            service_counts[event['service']] += 1
        
        for service, count in service_counts.items():
            content += f"- **{service}:** {count} operations\n"
        
        content += f"""
---

## 🎯 ANALYSIS SUMMARY

**Status:** {'✅ SUCCESS' if any('APP-CREATE-END' in e['operation'] for e in self.timeline_events) else '❌ INCOMPLETE'}  
**Total Duration:** {metrics['total_duration']:.1f}ms  
**Critical Path:** STYX → JOVE → HERCULES → External Services  

---

*Generated by App Timeline Generator v1.0*  
*Log Directory: {self.log_directory}*  
*Generated Events: {len(self.timeline_events)}*
"""
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"✅ Report generated successfully: {output_file}")
        return output_file
    
    def generate_timeline(self, app_uuid, output_file=None):
        """Main method to generate complete timeline for an app UUID"""
        self.app_uuid = app_uuid
        
        print(f"🚀 Starting timeline generation for app UUID: {app_uuid}")
        print(f"📁 Log directory: {self.log_directory}")
        
        # Step 1: Find reference IDs
        if not self.find_reference_ids(app_uuid):
            print("❌ Could not find reference IDs for the given app UUID")
            return None
        
        # Step 2: Extract timeline events
        self.extract_timeline_events()
        
        if not self.timeline_events:
            print("❌ No timeline events found for the given app UUID")
            return None
        
        # Step 3: Generate report
        report_file = self.generate_markdown_report(output_file)
        
        print(f"🎉 Timeline generation completed successfully!")
        print(f"📄 Report saved to: {report_file}")
        
        return report_file

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_app_timeline.py <app_uuid> [log_directory]")
        print("Example: python3 generate_app_timeline.py be7fec8f-53b7-49f0-9c33-2009a65238ef")
        sys.exit(1)
    
    app_uuid = sys.argv[1]
    log_directory = sys.argv[2] if len(sys.argv) > 2 else "/home/nutanix/log_analyze/nucalm_logs/log"
    
    # Validate app UUID format
    if not re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', app_uuid):
        print(f"❌ Invalid app UUID format: {app_uuid}")
        sys.exit(1)
    
    # Check if log directory exists
    if not os.path.exists(log_directory):
        print(f"❌ Log directory not found: {log_directory}")
        sys.exit(1)
    
    # Generate timeline
    generator = AppTimelineGenerator(log_directory)
    result = generator.generate_timeline(app_uuid)
    
    if result:
        print(f"\n✅ Success! Timeline report generated: {result}")
    else:
        print(f"\n❌ Failed to generate timeline for app UUID: {app_uuid}")
        sys.exit(1)

if __name__ == "__main__":
    main()
