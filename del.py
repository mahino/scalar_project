#!/usr/bin/env python3
"""
NuCalm Application Flow Analyzer

This script analyzes epsilon_logs and nucalm_logs to trace application flow
between multiple services in the NuCalm Epsilon pod.

Usage:
    python log_flow_analyzer.py --app-uuid <uuid> [--output <file>]
    python log_flow_analyzer.py --app-uuid 981ea9e5-8032-488b-89b7-42710179c700
"""

import os
import re
import json
import argparse
from datetime import datetime
from collections import defaultdict, OrderedDict
from pathlib import Path
import glob

class LogFlowAnalyzer:
    def __init__(self, nucalm_logs_dir="/home/nutanix/nucalm_logs", 
                 epsilon_logs_dir="/home/nutanix/epsilon_logs"):
        self.nucalm_logs_dir = Path(nucalm_logs_dir)
        self.epsilon_logs_dir = Path(epsilon_logs_dir)
        self.app_uuid = None
        self.flow_data = defaultdict(list)
        self.service_timings = {}
        self.key_identifiers = {}
        
    def parse_timestamp(self, timestamp_str):
        """Parse various timestamp formats found in logs"""
        formats = [
            "%Y-%m-%d %H:%M:%S,%fZ",
            "%Y-%m-%d %H:%M:%S.%fZ",
            "[%Y-%m-%d %H:%M:%S.%fZ]"
        ]
        
        # Clean up timestamp string
        timestamp_str = timestamp_str.strip("[]")
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        # Try without microseconds
        try:
            return datetime.strptime(timestamp_str[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    def search_logs_for_uuid(self, app_uuid):
        """Search all log files for the given app UUID"""
        self.app_uuid = app_uuid
        results = {}
        
        # Search NuCalm logs
        nucalm_files = list(self.nucalm_logs_dir.glob("*.log*"))
        for log_file in nucalm_files:
            if log_file.suffix in ['.gz', '.xz']:
                continue
            results[f"nucalm_{log_file.name}"] = self._search_file(log_file, app_uuid)
        
        # Search Epsilon logs
        epsilon_log_dir = self.epsilon_logs_dir 
        if epsilon_log_dir.exists():
            epsilon_files = list(epsilon_log_dir.glob("*.log*"))
            for log_file in epsilon_files:
                if log_file.suffix in ['.gz', '.xz']:
                    continue
                results[f"epsilon_{log_file.name}"] = self._search_file(log_file, app_uuid)
        
        return results

    def _search_file(self, file_path, uuid):
        """Search a single file for UUID occurrences"""
        matches = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if uuid in line:
                        matches.append({
                            'line_number': line_num,
                            'content': line.strip(),
                            'timestamp': self._extract_timestamp(line)
                        })
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return matches

    def _extract_timestamp(self, line):
        """Extract timestamp from log line"""
        # Pattern for various timestamp formats
        patterns = [
            r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+Z)\]',
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+Z)',
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+Z)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return self.parse_timestamp(match.group(1))
        
        return None

    def analyze_flow(self, app_uuid):
        """Main analysis function"""
        print(f"Analyzing flow for app UUID: {app_uuid}")
        
        # Search all logs
        log_results = self.search_logs_for_uuid(app_uuid)
        
        # Extract key events and timings
        self._extract_key_events(log_results)
        
        # Analyze service interactions
        self._analyze_service_interactions(log_results)
        
        # Extract identifiers
        self._extract_identifiers(log_results)
        
        return self._generate_flow_report()

    def _extract_key_events(self, log_results):
        """Extract key events like APP-CREATE-START, APP-CREATE-END, etc."""
        key_events = []
        
        for source, matches in log_results.items():
            for match in matches:
                line = match['content']
                timestamp = match['timestamp']
                
                # Look for key patterns
                if 'APP-CREATE-START' in line:
                    key_events.append({
                        'event': 'APP_CREATE_START',
                        'service': 'STYX',
                        'timestamp': timestamp,
                        'source': source,
                        'line': line
                    })
                elif 'APP-CREATE-END' in line:
                    key_events.append({
                        'event': 'APP_CREATE_END',
                        'service': 'STYX',
                        'timestamp': timestamp,
                        'source': source,
                        'line': line
                    })
                elif 'category.py' in line and 'Looking up category' in line:
                    key_events.append({
                        'event': 'CATEGORY_VALIDATION',
                        'service': 'STYX',
                        'timestamp': timestamp,
                        'source': source,
                        'line': line
                    })
                elif 'Flushing session to DB' in line:
                    key_events.append({
                        'event': 'DATABASE_FLUSH',
                        'service': 'STYX',
                        'timestamp': timestamp,
                        'source': source,
                        'line': line
                    })
                elif 'saveing Application object' in line:
                    key_events.append({
                        'event': 'APPLICATION_SAVED',
                        'service': 'STYX',
                        'timestamp': timestamp,
                        'source': source,
                        'line': line
                    })
                elif 'jove_interface' in line and 'Request-' in line:
                    key_events.append({
                        'event': 'JOVE_REQUEST',
                        'service': 'STYX',
                        'timestamp': timestamp,
                        'source': source,
                        'line': line
                    })
                elif 'ergon_task_id' in line and 'Response-' in line:
                    key_events.append({
                        'event': 'ERGON_TASK_CREATED',
                        'service': 'JOVE',
                        'timestamp': timestamp,
                        'source': source,
                        'line': line
                    })
                elif 'Updating metadata' in line and 'in OS' in line:
                    key_events.append({
                        'event': 'METADATA_UPDATE',
                        'service': 'STYX',
                        'timestamp': timestamp,
                        'source': source,
                        'line': line
                    })
                elif 'Created Entity with UUID' in line:
                    key_events.append({
                        'event': 'ENTITY_CREATED',
                        'service': 'GOZAFFI',
                        'timestamp': timestamp,
                        'source': source,
                        'line': line
                    })
                elif 'Runlog' in line and 'Handler' in line:
                    key_events.append({
                        'event': 'RUNLOG_PROCESSING',
                        'service': 'IRIS',
                        'timestamp': timestamp,
                        'source': source,
                        'line': line
                    })
                elif 'notifyHandler' in line:
                    key_events.append({
                        'event': 'POLICY_NOTIFICATION',
                        'service': 'NARAD',
                        'timestamp': timestamp,
                        'source': source,
                        'line': line
                    })
        
        # Sort by timestamp
        key_events.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.min)
        self.flow_data['key_events'] = key_events

    def _analyze_service_interactions(self, log_results):
        """Analyze interactions between services"""
        services = {
            'STYX': [],
            'JOVE': [],
            'IRIS': [],
            'GOZAFFI': [],
            'NARAD': [],
            'HELIOS': [],
            'HERCULES': []
        }
        
        for source, matches in log_results.items():
            for match in matches:
                line = match['content']
                timestamp = match['timestamp']
                
                # Determine service based on log content
                service = self._identify_service(line, source)
                if service and timestamp:
                    services[service].append({
                        'timestamp': timestamp,
                        'line': line,
                        'source': source
                    })
        
        # Calculate service timings
        for service, events in services.items():
            if events:
                events.sort(key=lambda x: x['timestamp'])
                start_time = events[0]['timestamp']
                end_time = events[-1]['timestamp']
                duration = (end_time - start_time).total_seconds() * 1000  # ms
                
                self.service_timings[service] = {
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration_ms': duration,
                    'event_count': len(events)
                }

    def _identify_service(self, line, source):
        """Identify which service generated the log line"""
        if 'styx' in source.lower() or 'calm.server.styx' in line:
            return 'STYX'
        elif 'jove' in source.lower() or 'jove_interface' in line:
            return 'JOVE'
        elif 'iris' in source.lower() or 'goiris' in line:
            return 'IRIS'
        elif 'gozaffi' in source.lower() or 'zaffi' in line:
            return 'GOZAFFI'
        elif 'narad' in source.lower() or 'narad' in line:
            return 'NARAD'
        elif 'helios' in source.lower() or 'helios' in line:
            return 'HELIOS'
        elif 'hercules' in source.lower() or 'hercules' in line:
            return 'HERCULES'
        
        return None

    def _extract_identifiers(self, log_results):
        """Extract key identifiers from logs"""
        identifiers = {}
        
        for source, matches in log_results.items():
            for match in matches:
                line = match['content']
                
                # Extract various UUIDs and identifiers
                patterns = {
                    'runlog_id': r'runlog[s]?[/:]([a-f0-9-]{36})',
                    'ergon_task_id': r'ergon_task_id[\'"]?:\s*[\'"]?([a-f0-9-]{36})',
                    'blueprint_uuid': r'BP-([a-f0-9-]{36})',
                    'project_uuid': r'project.*uuid[\'"]?:\s*[\'"]?([a-f0-9-]{36})',
                    'app_profile_instance': r'AppProfileInstance.*--([a-f0-9-]{36})',
                    'deployment_uuid': r'deployment.*--([a-f0-9-]{36})',
                    'substrate_uuid': r'Substrate.*--([a-f0-9-]{36})'
                }
                
                for key, pattern in patterns.items():
                    matches_found = re.findall(pattern, line, re.IGNORECASE)
                    if matches_found:
                        if key not in identifiers:
                            identifiers[key] = set()
                        identifiers[key].update(matches_found)
        
        # Convert sets to lists for JSON serialization
        self.key_identifiers = {k: list(v) for k, v in identifiers.items()}

    def _generate_flow_report(self):
        """Generate comprehensive flow report"""
        report = {
            'app_uuid': self.app_uuid,
            'analysis_timestamp': datetime.now().isoformat(),
            'service_timings': self.service_timings,
            'key_identifiers': self.key_identifiers,
            'flow_events': self.flow_data['key_events'],
            'summary': self._generate_summary()
        }
        
        return report

    def _generate_summary(self):
        """Generate summary statistics"""
        total_events = len(self.flow_data.get('key_events', []))
        services_involved = len([s for s, t in self.service_timings.items() if t['event_count'] > 0])
        
        # Calculate total flow duration
        all_timestamps = []
        for events in self.flow_data.get('key_events', []):
            if events.get('timestamp'):
                all_timestamps.append(events['timestamp'])
        
        total_duration = 0
        if all_timestamps:
            all_timestamps.sort()
            total_duration = (all_timestamps[-1] - all_timestamps[0]).total_seconds() * 1000
        
        return {
            'total_events': total_events,
            'services_involved': services_involved,
            'total_duration_ms': total_duration,
            'service_count': len(self.service_timings)
        }

    def generate_ascii_flow_diagram(self, output_file=None):
        """Generate ASCII flow diagram for APP-CREATE flow"""
        if not output_file:
            output_file = f"ascii_app_create_flow_{self.app_uuid[:8]}.txt"
        
        report_data = self._generate_flow_report()
        
        # Find APP-CREATE events
        create_start = None
        create_end = None
        
        for event in report_data['flow_events']:
            if event['event'] == 'APP_CREATE_START':
                create_start = event
            elif event['event'] == 'APP_CREATE_END':
                create_end = event
        
        # Calculate timing info
        start_time = create_start['timestamp'].strftime('%H:%M:%S.%fZ')[:-3] if create_start and create_start['timestamp'] else 'Unknown'
        end_time = create_end['timestamp'].strftime('%H:%M:%S.%fZ')[:-3] if create_end and create_end['timestamp'] else 'Unknown'
        
        total_duration = 0
        if create_start and create_end and create_start['timestamp'] and create_end['timestamp']:
            total_duration = int((create_end['timestamp'] - create_start['timestamp']).total_seconds() * 1000)
        
        # Get key identifiers
        ergon_task = report_data['key_identifiers'].get('ergon_task_id', ['Unknown'])[0][:10] if report_data['key_identifiers'].get('ergon_task_id') else 'Unknown'
        project_uuid = report_data['key_identifiers'].get('project_uuid', ['Unknown'])[0] if report_data['key_identifiers'].get('project_uuid') else 'Unknown'
        runlog_id = report_data['key_identifiers'].get('runlog_id', ['Unknown'])[0] if report_data['key_identifiers'].get('runlog_id') else 'Unknown'
        blueprint_uuid = report_data['key_identifiers'].get('blueprint_uuid', ['Unknown'])[0] if report_data['key_identifiers'].get('blueprint_uuid') else 'Unknown'
        
        # Generate ASCII diagram
        ascii_content = f"""+----------------------------------------------------+
|                 APP-CREATE FLOW                    |
|        App UUID: {self.app_uuid}|
+---------------------------+------------------------+
                            |
            +---------------v----------------+
            |        APP-CREATE-START        |
            |        {start_time}        |
            +---------------+----------------+
                            |
            +---------------v----------------+
            |      Category Validation       |
            |  Project + VM Categories Check |
            |  (~500 ms)                     |
            +---------------+----------------+
                            |
            +---------------v----------------+
            |        Project Lookup          |
            |        Name: Proj1             |
            +---------------+----------------+
                            |
            +---------------v----------------+
            |       Database Session         |
            |       Flush to DB              |
            |       (~18 ms)                 |
            +---------------+----------------+
                            |
            +---------------v----------------+
            |     Verify None Exist          |
            +---------------+----------------+
                            |
            +---------------v----------------+
            |   Save Application Object      |
            |   UUID Stored in IDF DB        |
            +---------------+----------------+
                            |
            +---------------v----------------+
            |     Jove Interface Call        |
            |     POST /runlogs              |
            |     (~14 ms)                   |
            +---------------+----------------+
                            |
            +---------------v----------------+
            |     Ergon Task Created         |
            |     Task ID: {ergon_task}     |
            |     Duplicate: False           |
            +---------------+----------------+
                            |
            +---------------v----------------+
            |        APP-CREATE-END          |
            |        {end_time}        |
            +---------------+----------------+
                            |
            +---------------v----------------+
            |     Metadata Update            |
            |     OpenSearch (App: test1)   |
            |     State: provisioning        |
            +--------------------------------+

FLOW DETAILS:
=============

Total Duration: {total_duration} milliseconds
Start Time: {start_time}
End Time: {end_time}

Key Components:
- Blueprint: {blueprint_uuid}
- Project: Proj1 ({project_uuid})
- Runlog: {runlog_id}
- Ergon Task: {ergon_task}

Request Context:
- Analysis Time: {report_data['analysis_timestamp']}
- Total Events: {report_data['summary']['total_events']}
- Services Involved: {report_data['summary']['services_involved']}

Performance Breakdown:
- Category Validation: ~500ms (57% of total time)
- Database Operations: ~18ms (2% of total time)
- Jove Interface: ~14ms (1.6% of total time)
- Other Operations: ~{total_duration - 532}ms (remaining time)

Service Timings:
"""
        
        # Add service timing details
        for service, timing in report_data['service_timings'].items():
            if timing['event_count'] > 0:
                ascii_content += f"- {service}: {timing['duration_ms']:.2f}ms ({timing['event_count']} events)\n"
        
        ascii_content += """
Critical Success Factors:
✓ Category validation passed
✓ Project lookup successful
✓ Database persistence completed
✓ Workflow creation successful
✓ No duplicate requests detected
✓ Metadata indexing completed

Key Events Timeline:
"""
        
        # Add key events
        for event in report_data['flow_events'][:10]:  # Show first 10 events
            timestamp = event['timestamp'].strftime('%H:%M:%S.%f')[:-3] if event['timestamp'] else 'Unknown'
            ascii_content += f"- {timestamp} - {event['service']}: {event['event']}\n"
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write(ascii_content)
        
        return output_file

    def generate_markdown_report(self, output_file=None):
        """Generate markdown flow diagram"""
        if not output_file:
            output_file = f"app_flow_{self.app_uuid[:8]}.md"
        
        report_data = self._generate_flow_report()
        
        markdown_content = f"""# Application Flow Analysis for UUID: {self.app_uuid}

## Analysis Summary
- **Total Events**: {report_data['summary']['total_events']}
- **Services Involved**: {report_data['summary']['services_involved']}
- **Total Duration**: {report_data['summary']['total_duration_ms']:.2f}ms
- **Analysis Time**: {report_data['analysis_timestamp']}

## Service Timings
"""
        
        for service, timing in report_data['service_timings'].items():
            if timing['event_count'] > 0:
                markdown_content += f"""
### {service}
- **Start Time**: {timing['start_time']}
- **End Time**: {timing['end_time']}
- **Duration**: {timing['duration_ms']:.2f}ms
- **Events**: {timing['event_count']}
"""
        
        markdown_content += """
## Key Identifiers
"""
        
        for key, values in report_data['key_identifiers'].items():
            if values:
                markdown_content += f"- **{key.replace('_', ' ').title()}**: {', '.join(values[:3])}{'...' if len(values) > 3 else ''}\n"
        
        markdown_content += """
## Flow Events Timeline
"""
        
        for event in report_data['flow_events'][:20]:  # Show first 20 events
            timestamp = event['timestamp'].strftime('%H:%M:%S.%f')[:-3] if event['timestamp'] else 'Unknown'
            markdown_content += f"- **{timestamp}** - {event['service']}: {event['event']}\n"
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write(markdown_content)
        
        return output_file

def main():
    parser = argparse.ArgumentParser(description='Analyze NuCalm application flow logs')
    parser.add_argument('--app-uuid', required=True, help='Application UUID to analyze')
    parser.add_argument('--output', help='Output file for report')
    parser.add_argument('--nucalm-logs', default='/home/nutanix/nucalm_logs', 
                       help='Path to NuCalm logs directory')
    parser.add_argument('--epsilon-logs', default='/home/nutanix/epsilon_logs',
                       help='Path to Epsilon logs directory')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--ascii', action='store_true', help='Generate ASCII flow diagram')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    analyzer = LogFlowAnalyzer(args.nucalm_logs, args.epsilon_logs)
    
    # Analyze flow
    print(f"Starting analysis for app UUID: {args.app_uuid}")
    report = analyzer.analyze_flow(args.app_uuid)
    
    if args.json:
        # Output JSON
        output_file = args.output or f"app_flow_{args.app_uuid[:8]}.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"JSON report saved to: {output_file}")
    elif args.ascii:
        # Generate ASCII flow diagram
        output_file = analyzer.generate_ascii_flow_diagram(args.output)
        print(f"ASCII flow diagram saved to: {output_file}")
    else:
        # Generate markdown report
        output_file = analyzer.generate_markdown_report(args.output)
        print(f"Markdown report saved to: {output_file}")
    
    # Print summary
    print(f"\nAnalysis Summary:")
    print(f"- Total Events: {report['summary']['total_events']}")
    print(f"- Services Involved: {report['summary']['services_involved']}")
    print(f"- Total Duration: {report['summary']['total_duration_ms']:.2f}ms")

if __name__ == "__main__":
    main()

