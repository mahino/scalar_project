#!/bin/bash

# Payload Scaler Service Management Script
# Usage: ./manage_service.sh [start|stop|restart|status]

PORT=5001
SERVICE_NAME="python3 app.py"
PROJECT_DIR="/Users/mohan.as1/Documents/scalar_project"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if service is running
check_service() {
    local pids=$(lsof -ti:$PORT 2>/dev/null)
    if [ -n "$pids" ]; then
        echo -e "${GREEN}Service is running on port $PORT${NC}"
        echo "PIDs: $pids"
        lsof -i:$PORT
        return 0
    else
        echo -e "${RED}No service running on port $PORT${NC}"
        return 1
    fi
}

# Function to stop service
stop_service() {
    echo -e "${YELLOW}Stopping service on port $PORT...${NC}"
    local pids=$(lsof -ti:$PORT 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo "Found PIDs: $pids"
        for pid in $pids; do
            echo "Killing PID: $pid"
            kill -9 $pid 2>/dev/null
        done
        sleep 2
        
        # Verify service is stopped
        local remaining_pids=$(lsof -ti:$PORT 2>/dev/null)
        if [ -z "$remaining_pids" ]; then
            echo -e "${GREEN}Service stopped successfully${NC}"
        else
            echo -e "${RED}Warning: Some processes may still be running: $remaining_pids${NC}"
        fi
    else
        echo -e "${YELLOW}No service running on port $PORT${NC}"
    fi
}

# Function to start service
start_service() {
    echo -e "${BLUE}Starting service...${NC}"
    
    # Check if already running
    if check_service >/dev/null 2>&1; then
        echo -e "${YELLOW}Service already running. Use 'restart' to restart it.${NC}"
        return 1
    fi
    
    # Change to project directory
    cd "$PROJECT_DIR" || {
        echo -e "${RED}Error: Cannot change to project directory: $PROJECT_DIR${NC}"
        return 1
    }
    
    # Start service in background
    echo "Starting $SERVICE_NAME in background..."
    nohup python3 app.py > service.log 2>&1 &
    local service_pid=$!
    
    # Wait a moment for service to start
    sleep 3
    
    # Verify service started
    if check_service >/dev/null 2>&1; then
        echo -e "${GREEN}Service started successfully (PID: $service_pid)${NC}"
        echo "Logs: tail -f $PROJECT_DIR/service.log"
    else
        echo -e "${RED}Failed to start service${NC}"
        echo "Check logs: cat $PROJECT_DIR/service.log"
        return 1
    fi
}

# Function to restart service
restart_service() {
    echo -e "${BLUE}Restarting service...${NC}"
    stop_service
    sleep 2
    start_service
}

# Function to show service status
show_status() {
    echo -e "${BLUE}=== Payload Scaler Service Status ===${NC}"
    echo "Port: $PORT"
    echo "Service: $SERVICE_NAME"
    echo "Project Directory: $PROJECT_DIR"
    echo ""
    check_service
}

# Function to show logs
show_logs() {
    local log_file="$PROJECT_DIR/service.log"
    if [ -f "$log_file" ]; then
        echo -e "${BLUE}=== Service Logs (last 20 lines) ===${NC}"
        tail -20 "$log_file"
        echo ""
        echo -e "${YELLOW}To follow logs in real-time: tail -f $log_file${NC}"
    else
        echo -e "${RED}Log file not found: $log_file${NC}"
    fi
}

# Function to show help
show_help() {
    echo -e "${BLUE}=== Payload Scaler Service Manager ===${NC}"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Start the service"
    echo "  stop      - Stop the service"
    echo "  restart   - Restart the service"
    echo "  status    - Show service status"
    echo "  logs      - Show recent logs"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 restart"
    echo "  $0 status"
}

# Main script logic
case "${1:-status}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
