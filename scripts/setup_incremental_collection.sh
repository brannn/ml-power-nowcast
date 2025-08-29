#!/bin/bash
#
# Setup Incremental CAISO Data Collection on macOS
#
# This script sets up automated incremental data collection using macOS launchd.
# The job will run every 30 minutes to collect fresh CAISO power data.
#
# Usage:
#   bash scripts/setup_incremental_collection.sh [install|uninstall|status|logs]
#

set -e

# Configuration
PROJECT_DIR="/Users/bran/Work/model-power-nowcast"
PLIST_FILE="com.caiso.incremental.plist"
PLIST_SOURCE="$PROJECT_DIR/scripts/$PLIST_FILE"
PLIST_TARGET="$HOME/Library/LaunchAgents/$PLIST_FILE"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
COLLECTION_SCRIPT="$PROJECT_DIR/scripts/incremental_collection_macos.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if we're in the right directory
    if [ ! -f "$PROJECT_DIR/scripts/incremental_collection_macos.py" ]; then
        print_error "Collection script not found: $COLLECTION_SCRIPT"
        exit 1
    fi
    
    # Check if virtual environment exists
    if [ ! -f "$VENV_PYTHON" ]; then
        print_error "Virtual environment not found: $VENV_PYTHON"
        exit 1
    fi
    
    # Check if plist file exists
    if [ ! -f "$PLIST_SOURCE" ]; then
        print_error "Plist file not found: $PLIST_SOURCE"
        exit 1
    fi
    
    # Create logs directory
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/data/incremental"
    
    print_success "Prerequisites check passed"
}

install_job() {
    print_status "Installing incremental data collection job..."
    
    check_prerequisites
    
    # Copy plist to LaunchAgents directory
    mkdir -p "$HOME/Library/LaunchAgents"
    cp "$PLIST_SOURCE" "$PLIST_TARGET"
    
    # Load the job
    launchctl load "$PLIST_TARGET"
    
    print_success "Incremental collection job installed and started"
    print_status "Job will run every 30 minutes"
    print_status "Logs will be written to: $PROJECT_DIR/logs/"
    
    # Test the script manually
    print_status "Testing collection script..."
    cd "$PROJECT_DIR"
    if "$VENV_PYTHON" "$COLLECTION_SCRIPT" --hours 1 --quiet; then
        print_success "Test collection completed successfully"
    else
        print_warning "Test collection failed - check logs for details"
    fi
}

uninstall_job() {
    print_status "Uninstalling incremental data collection job..."
    
    # Unload the job if it's loaded
    if launchctl list | grep -q "com.caiso.incremental"; then
        launchctl unload "$PLIST_TARGET" 2>/dev/null || true
        print_success "Job unloaded"
    fi
    
    # Remove plist file
    if [ -f "$PLIST_TARGET" ]; then
        rm "$PLIST_TARGET"
        print_success "Plist file removed"
    fi
    
    print_success "Incremental collection job uninstalled"
}

show_status() {
    print_status "Incremental Data Collection Status"
    echo "=================================="
    
    # Check if job is loaded
    if launchctl list | grep -q "com.caiso.incremental"; then
        print_success "Job is loaded and active"
        
        # Show job details
        echo ""
        print_status "Job Details:"
        launchctl list | grep "com.caiso.incremental"
        
    else
        print_warning "Job is not loaded"
    fi
    
    # Check if plist file exists
    if [ -f "$PLIST_TARGET" ]; then
        print_success "Plist file exists: $PLIST_TARGET"
    else
        print_warning "Plist file not found: $PLIST_TARGET"
    fi
    
    # Check recent logs
    echo ""
    print_status "Recent Log Files:"
    ls -la "$PROJECT_DIR/logs/" | grep incremental | tail -5 || print_warning "No log files found"
    
    # Check incremental data
    echo ""
    print_status "Incremental Data Status:"
    if [ -f "$PROJECT_DIR/data/incremental/caiso_recent.parquet" ]; then
        file_size=$(ls -lh "$PROJECT_DIR/data/incremental/caiso_recent.parquet" | awk '{print $5}')
        file_date=$(ls -l "$PROJECT_DIR/data/incremental/caiso_recent.parquet" | awk '{print $6, $7, $8}')
        print_success "Data file exists: $file_size (modified: $file_date)"
    else
        print_warning "No incremental data file found"
    fi
}

show_logs() {
    print_status "Recent Incremental Collection Logs"
    echo "=================================="
    
    # Show recent application logs
    if [ -f "$PROJECT_DIR/logs/incremental_$(date +%Y%m%d).log" ]; then
        echo ""
        print_status "Today's Application Log (last 20 lines):"
        tail -20 "$PROJECT_DIR/logs/incremental_$(date +%Y%m%d).log"
    fi
    
    # Show recent stdout logs
    if [ -f "$PROJECT_DIR/logs/incremental_stdout.log" ]; then
        echo ""
        print_status "Standard Output Log (last 10 lines):"
        tail -10 "$PROJECT_DIR/logs/incremental_stdout.log"
    fi
    
    # Show recent stderr logs
    if [ -f "$PROJECT_DIR/logs/incremental_stderr.log" ]; then
        echo ""
        print_status "Standard Error Log (last 10 lines):"
        tail -10 "$PROJECT_DIR/logs/incremental_stderr.log"
    fi
}

run_manual_test() {
    print_status "Running manual test collection..."
    
    check_prerequisites
    
    cd "$PROJECT_DIR"
    "$VENV_PYTHON" "$COLLECTION_SCRIPT" --hours 2
    
    print_success "Manual test completed"
}

# Main script logic
case "${1:-install}" in
    install)
        install_job
        ;;
    uninstall)
        uninstall_job
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    test)
        run_manual_test
        ;;
    *)
        echo "Usage: $0 [install|uninstall|status|logs|test]"
        echo ""
        echo "Commands:"
        echo "  install   - Install and start the incremental collection job"
        echo "  uninstall - Stop and remove the incremental collection job"
        echo "  status    - Show current job status and data"
        echo "  logs      - Show recent log files"
        echo "  test      - Run a manual test collection"
        echo ""
        echo "Default: install"
        exit 1
        ;;
esac
