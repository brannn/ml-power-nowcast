#!/bin/bash
#
# Setup Automated ML Pipeline on macOS
#
# This script sets up automated ML model training and deployment using macOS launchd.
# The pipeline runs every 6 hours to keep models fresh with the latest data.
#
# Usage:
#   bash scripts/setup_ml_pipeline.sh [install|uninstall|status|logs|test]
#

set -e

# Configuration
PROJECT_DIR="/Users/bran/Work/model-power-nowcast"
PLIST_FILE="com.caiso.ml_pipeline.plist"
PLIST_SOURCE="$PROJECT_DIR/scripts/$PLIST_FILE"
PLIST_TARGET="$HOME/Library/LaunchAgents/$PLIST_FILE"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
PIPELINE_SCRIPT="$PROJECT_DIR/scripts/automated_ml_pipeline.py"

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
    if [ ! -f "$PIPELINE_SCRIPT" ]; then
        print_error "ML pipeline script not found: $PIPELINE_SCRIPT"
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
    
    # Check for required data
    if [ ! -f "$PROJECT_DIR/data/master/caiso_california_only.parquet" ]; then
        print_warning "Master dataset not found - pipeline may fail"
    fi
    
    # Create necessary directories
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/data/production_models"
    mkdir -p "$PROJECT_DIR/data/model_backups"
    
    print_success "Prerequisites check passed"
}

install_job() {
    print_status "Installing automated ML pipeline job..."
    
    check_prerequisites
    
    # Copy plist to LaunchAgents directory
    mkdir -p "$HOME/Library/LaunchAgents"
    cp "$PLIST_SOURCE" "$PLIST_TARGET"
    
    # Load the job
    launchctl load "$PLIST_TARGET"
    
    print_success "Automated ML pipeline job installed and started"
    print_status "Pipeline will run every 6 hours at 2 AM, 8 AM, 2 PM, 8 PM"
    print_status "Logs will be written to: $PROJECT_DIR/logs/"
    
    # Test the script manually
    print_status "Testing ML pipeline script..."
    cd "$PROJECT_DIR"
    if "$VENV_PYTHON" "$PIPELINE_SCRIPT" --target-zones NP15 --quiet --skip-cleanup; then
        print_success "Test ML pipeline run completed successfully"
    else
        print_warning "Test ML pipeline run failed - check logs for details"
    fi
}

uninstall_job() {
    print_status "Uninstalling automated ML pipeline job..."
    
    # Unload the job if it's loaded
    if launchctl list | grep -q "com.caiso.ml_pipeline"; then
        launchctl unload "$PLIST_TARGET" 2>/dev/null || true
        print_success "Job unloaded"
    fi
    
    # Remove plist file
    if [ -f "$PLIST_TARGET" ]; then
        rm "$PLIST_TARGET"
        print_success "Plist file removed"
    fi
    
    print_success "Automated ML pipeline job uninstalled"
}

show_status() {
    print_status "Automated ML Pipeline Status"
    echo "============================="
    
    # Check if job is loaded
    if launchctl list | grep -q "com.caiso.ml_pipeline"; then
        print_success "Job is loaded and active"
        
        # Show job details
        echo ""
        print_status "Job Details:"
        launchctl list | grep "com.caiso.ml_pipeline"
        
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
    ls -la "$PROJECT_DIR/logs/" | grep ml_pipeline | tail -5 || print_warning "No ML pipeline log files found"
    
    # Check production models
    echo ""
    print_status "Production Models Status:"
    if [ -f "$PROJECT_DIR/data/production_models/enhanced_model_current.joblib" ]; then
        file_size=$(ls -lh "$PROJECT_DIR/data/production_models/enhanced_model_current.joblib" | awk '{print $5}')
        file_date=$(ls -l "$PROJECT_DIR/data/production_models/enhanced_model_current.joblib" | awk '{print $6, $7, $8}')
        print_success "Enhanced model exists: $file_size (modified: $file_date)"
    else
        print_warning "No enhanced production model found"
    fi
    
    if [ -f "$PROJECT_DIR/data/production_models/baseline_model_current.joblib" ]; then
        file_size=$(ls -lh "$PROJECT_DIR/data/production_models/baseline_model_current.joblib" | awk '{print $5}')
        file_date=$(ls -l "$PROJECT_DIR/data/production_models/baseline_model_current.joblib" | awk '{print $6, $7, $8}')
        print_success "Baseline model exists: $file_size (modified: $file_date)"
    else
        print_warning "No baseline production model found"
    fi
    
    # Check model metadata
    if [ -f "$PROJECT_DIR/data/production_models/deployment_metadata.json" ]; then
        echo ""
        print_status "Model Deployment Info:"
        cd "$PROJECT_DIR"
        "$VENV_PYTHON" -c "
import json
try:
    with open('data/production_models/deployment_metadata.json', 'r') as f:
        metadata = json.load(f)
    print(f'   Deployed at: {metadata.get(\"deployed_at\", \"Unknown\")}')
    print(f'   Baseline available: {metadata.get(\"baseline_available\", False)}')
    print(f'   Enhanced available: {metadata.get(\"enhanced_available\", False)}')
except Exception as e:
    print(f'   Error reading metadata: {e}')
" 2>/dev/null || print_warning "Could not read deployment metadata"
    fi
}

show_logs() {
    print_status "Recent Automated ML Pipeline Logs"
    echo "=================================="
    
    # Show recent application logs
    if [ -f "$PROJECT_DIR/logs/automated_ml_$(date +%Y%m%d).log" ]; then
        echo ""
        print_status "Today's Application Log (last 20 lines):"
        tail -20 "$PROJECT_DIR/logs/automated_ml_$(date +%Y%m%d).log"
    fi
    
    # Show recent stdout logs
    if [ -f "$PROJECT_DIR/logs/ml_pipeline_stdout.log" ]; then
        echo ""
        print_status "Standard Output Log (last 10 lines):"
        tail -10 "$PROJECT_DIR/logs/ml_pipeline_stdout.log"
    fi
    
    # Show recent stderr logs
    if [ -f "$PROJECT_DIR/logs/ml_pipeline_stderr.log" ]; then
        echo ""
        print_status "Standard Error Log (last 10 lines):"
        tail -10 "$PROJECT_DIR/logs/ml_pipeline_stderr.log"
    fi
}

run_manual_test() {
    print_status "Running manual ML pipeline test..."
    
    check_prerequisites
    
    cd "$PROJECT_DIR"
    "$VENV_PYTHON" "$PIPELINE_SCRIPT" --target-zones NP15 --skip-cleanup
    
    print_success "Manual ML pipeline test completed"
}

show_schedule() {
    print_status "ML Pipeline Schedule"
    echo "==================="
    echo ""
    echo "The automated ML pipeline runs every 6 hours:"
    echo "  🌙 2:00 AM  - Full model retraining + dataset refresh"
    echo "  🌅 8:00 AM  - Incremental update + model refresh"
    echo "  ☀️  2:00 PM  - Incremental update + model refresh"
    echo "  🌆 8:00 PM  - Incremental update + model refresh"
    echo ""
    echo "Each run includes:"
    echo "  • Dataset merging with latest incremental data"
    echo "  • Model training with fresh data"
    echo "  • Model validation and performance checks"
    echo "  • Production model deployment"
    echo "  • Backup creation and cleanup"
    echo ""
    echo "Models are deployed to:"
    echo "  • data/production_models/baseline_model_current.joblib"
    echo "  • data/production_models/enhanced_model_current.joblib"
    echo ""
    echo "Dashboard integration:"
    echo "  • Models are automatically refreshed for serving"
    echo "  • Predictions use the latest trained models"
    echo "  • Fallback to previous models if training fails"
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
    schedule)
        show_schedule
        ;;
    *)
        echo "Usage: $0 [install|uninstall|status|logs|test|schedule]"
        echo ""
        echo "Commands:"
        echo "  install   - Install and start the automated ML pipeline job"
        echo "  uninstall - Stop and remove the automated ML pipeline job"
        echo "  status    - Show current job status and model deployment"
        echo "  logs      - Show recent log files"
        echo "  test      - Run a manual ML pipeline test"
        echo "  schedule  - Show the pipeline schedule and details"
        echo ""
        echo "Default: install"
        exit 1
        ;;
esac
