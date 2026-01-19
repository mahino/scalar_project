# Log Analyzer & Flow Visualization System

## Overview

The Log Analyzer is a comprehensive end-to-end system for analyzing microservice logs and visualizing application flow diagrams from Kubernetes clusters. It provides automated log collection, analysis, and real-time flow visualization capabilities.

## Features

### 🔗 **Dual Cluster Support**
- **PC Mode**: Prism Central clusters using Docker containers
- **NCM Mode**: Nutanix Cloud Manager using Kubernetes pods
- SSH connection to both cluster types
- Automated configuration setup (Docker validation for PC, kubeconfig for NCM)
- Support for multiple clusters simultaneously

### 🔍 **Service Discovery & Log Collection**
- **PC Mode**: Dynamic container discovery using Docker commands
- **NCM Mode**: Dynamic pod discovery in specified namespaces
- Intelligent service type detection (epsilon, ramp, telle, calm, etc.)
- **PC Mode**: Uses `docker cp` for log collection, special handling for epsilon container (`/home/epsilon/log`)
- **NCM Mode**: Uses `kubectl cp` for log collection from pods
- Preserves folder structure locally

### 🧠 **Log Analysis Engine**
- UUID-based application correlation across microservices
- Automatic extraction of:
  - Service names and operations
  - Start/end times and durations
  - Request/trace identifiers
  - Error states and status codes
- Cross-service interaction mapping

### 📊 **Flow Visualization**
- Interactive service-to-service flow diagrams
- Real-time rendering with directional arrows
- Time-based ordering and bottleneck highlighting
- Detailed service interaction views

### 🎯 **Application Management**
- Searchable application UUID selector
- Dynamic data loading without page reloads
- Application-level aggregation and metrics
- Export capabilities for flow diagrams

## Architecture

### Frontend Components
- **Analyzer UI**: Modern, responsive interface with progress indicators
- **Flow Diagram**: Interactive visualization with zoom and export features
- **Application Selector**: Dropdown with search and filtering capabilities
- **Progress Tracking**: Real-time status updates for each analysis step

### Backend Components
- **AnalyzerManager**: Core orchestration and workflow management
- **SSH Handler**: Secure connection management and command execution
- **Kubeconfig Manager**: Cluster configuration and validation
- **Pod Discovery**: Dynamic service detection and log path mapping
- **Log Collector**: Efficient file transfer and organization
- **Analysis Engine**: Pattern recognition and correlation algorithms

### Data Flow
```
PC IP Input → SSH Connect → Kubeconfig Setup → Pod Discovery → Log Collection → Analysis → Flow Visualization
```

## Usage

### 1. **Access the Analyzer**
- Navigate to the main application
- Click "Analyzer" in the left sidebar menu
- The analyzer workspace will open

### 2. **Select Cluster Type**
- Choose between **PC (Prism Central)** or **NCM (Nutanix Cloud Manager)**
- **PC Mode**: Uses Docker containers for log collection
- **NCM Mode**: Uses Kubernetes pods for log collection

### 3. **Connect to Cluster**
- Enter the cluster IP address (required)
- For NCM mode: Optionally modify the namespace (default: `ntnx-ncm-selfservice`)
- For PC mode: Namespace field is hidden (not applicable)
- Click "Connect & Analyze"

### 4. **Monitor Progress**
The system will automatically progress through:
- ✅ SSH Connection establishment
- ✅ Configuration setup (Docker validation for PC, kubeconfig for NCM)
- ✅ Service discovery (containers for PC, pods for NCM)
- ✅ Log collection from discovered services
- ✅ Log analysis and correlation

### 4. **Select Application**
- Once analysis completes, applications will appear in the dropdown
- Select an application UUID to view its flow diagram
- View service counts and interaction statistics

### 5. **Explore Flow Diagram**
- Interactive service nodes show operations and timing
- Click nodes for detailed interaction information
- Use controls to reset zoom or export diagrams
- Color coding indicates success/warning/error states

## Configuration

### Supported Services
The analyzer automatically detects and handles these service types:
- **epsilon**: Special PC container with logs in `/home/epsilon/log` (PC mode only)
- **ramp**: Resource and VM management
- **telle**: Telemetry and monitoring
- **calm**: Application lifecycle management
- **ncm**: Nutanix Cloud Manager
- **selfservice**: Self-service portal
- **api**: API gateway services
- **ui**: User interface services
- **gateway**: Network gateway
- **auth**: Authentication services

### Log Paths
Each service type has predefined log paths that vary by cluster type:

**PC Mode (Docker containers):**
```python
{
    'epsilon': ['/home/epsilon/log'],  # Special case for epsilon container
    'ramp': ['/var/log/ramp/ramp.log', '/var/log/ramp/error.log'],
    'telle': ['/var/log/telle/telle.log', '/var/log/telle/error.log'],
    # ... additional services
}
```

**NCM Mode (Kubernetes pods):**
```python
{
    'ramp': ['/var/log/ramp/ramp.log', '/var/log/ramp/error.log'],
    'telle': ['/var/log/telle/telle.log', '/var/log/telle/error.log'],
    'calm': ['/var/log/calm/calm.log', '/var/log/calm/error.log'],
    # ... additional services
}
```

### Cluster Type Configuration

**PC Mode (Prism Central):**
- Uses Docker containers for service discovery
- Log collection via `docker cp` commands
- Special handling for epsilon container: `docker cp epsilon:/home/epsilon/log .`
- No namespace configuration required

**NCM Mode (Nutanix Cloud Manager):**
- Uses Kubernetes pods for service discovery
- Log collection via `kubectl cp` commands
- Default namespace: `ntnx-ncm-selfservice`
- Configurable per analysis session
- Supports any valid Kubernetes namespace

## API Endpoints

### Core Analysis Endpoints
- `POST /api/analyzer/ssh-connect` - Test SSH connection
- `POST /api/analyzer/kubeconfig-setup` - Setup cluster configuration
- `POST /api/analyzer/discover-pods` - Discover pods in namespace
- `POST /api/analyzer/collect-logs` - Collect logs from pods
- `POST /api/analyzer/analyze-logs` - Analyze collected logs

### Data Retrieval Endpoints
- `POST /api/analyzer/get-flow` - Get application flow data
- `POST /api/analyzer/cleanup` - Clean up workspace

## Error Handling

### Connection Errors
- SSH timeout and authentication failures
- Network connectivity issues
- Invalid IP addresses or unreachable hosts

### Kubernetes Errors
- Kubeconfig generation failures
- Pod access permissions
- Namespace not found

### Log Collection Errors
- Missing log files or paths
- Permission denied on log access
- Large file handling and timeouts

### Analysis Errors
- Malformed log entries
- Missing UUID patterns
- Correlation failures across services

## Performance Considerations

### Scalability
- Handles large log volumes efficiently
- Streaming analysis for real-time processing
- Configurable timeout and retry mechanisms

### Memory Management
- Incremental log processing
- Automatic cleanup of temporary files
- Configurable cache sizes

### Network Optimization
- Compressed log transfer
- Parallel pod processing
- Connection pooling for multiple clusters

## Security

### SSH Security
- StrictHostKeyChecking disabled for automation
- Temporary key management
- Connection timeout enforcement

### Data Security
- Local workspace isolation
- Automatic cleanup capabilities
- No persistent credential storage

### Access Control
- Cluster-level access validation
- Namespace-based permissions
- Read-only log access

## Troubleshooting

### Common Issues

**SSH Connection Failed**
- Verify PC IP address is correct and reachable
- Ensure SSH service is running on the cluster
- Check network connectivity and firewall rules

**Kubeconfig Setup Failed**
- Verify `mspctl` command is available on the cluster
- Check cluster status and health
- Ensure proper permissions for kubeconfig generation

**No Pods Found**
- Verify namespace exists and contains pods
- Check pod status and readiness
- Ensure proper RBAC permissions

**Log Collection Failed**
- Verify log paths exist in the pods
- Check pod filesystem permissions
- Ensure sufficient disk space locally

**Analysis Found No Applications**
- Verify logs contain UUID patterns
- Check log format compatibility
- Ensure logs have sufficient data

### Debug Mode
Enable detailed logging by setting log level to DEBUG in the application configuration.

## Future Enhancements

### Planned Features
- **Multi-cluster Support**: Analyze multiple clusters simultaneously
- **Advanced Visualizations**: 3D flow diagrams and timeline views
- **Machine Learning**: Anomaly detection and pattern recognition
- **Real-time Monitoring**: Live log streaming and analysis
- **Custom Parsers**: Support for additional log formats
- **Performance Metrics**: Detailed timing and bottleneck analysis
- **Alert System**: Automated error detection and notifications
- **Export Options**: Multiple format support (PDF, SVG, JSON)

### Integration Opportunities
- **Grafana Integration**: Dashboard embedding and metrics export
- **Prometheus Integration**: Metrics collection and alerting
- **Elasticsearch Integration**: Advanced search and indexing
- **Slack/Teams Integration**: Automated notifications and reports

## Contributing

The analyzer system is designed with modularity and extensibility in mind:

### Adding New Services
1. Update `_extract_service_type()` with new service patterns
2. Add log paths in `_get_log_paths_for_service()`
3. Extend analysis patterns in `_extract_operation_from_line()`

### Custom Log Parsers
1. Implement new parser in `_analyze_log_file()`
2. Add service-specific operation extraction
3. Update correlation algorithms as needed

### Visualization Enhancements
1. Extend flow diagram rendering in `renderFlowDiagram()`
2. Add new visualization libraries (D3.js, Cytoscape.js, etc.)
3. Implement custom interaction patterns

## Support

For issues, questions, or feature requests related to the Log Analyzer system, please refer to the main application documentation or contact the development team.
