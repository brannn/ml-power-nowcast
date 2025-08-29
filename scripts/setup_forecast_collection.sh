#!/bin/bash
#
# Setup Weather Forecast Collection on macOS
#
# This script sets up automated weather forecast collection using macOS launchd.
# The job will run every 6 hours to collect fresh weather forecasts for CAISO zones.
#
# Usage:
#   bash scripts/setup_forecast_collection.sh [install|uninstall|status|logs|test]
#

set -e

# Configuration
PROJECT_DIR="/Users/bran/Work/model-power-nowcast"
PLIST_FILE="com.caiso.forecasts.plist"
PLIST_SOURCE="$PROJECT_DIR/scripts/$PLIST_FILE"
PLIST_TARGET="$HOME/Library/LaunchAgents/$PLIST_FILE"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
COLLECTION_SCRIPT="$PROJECT_DIR/scripts/collect_weather_forecasts.py"

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
    if [ ! -f "$COLLECTION_SCRIPT" ]; then
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
    
    # Create necessary directories
    mkdir -p "$PROJECT_DIR/logs"
    mkdir -p "$PROJECT_DIR/data/forecasts"
    
    print_success "Prerequisites check passed"
}

install_job() {
    print_status "Installing weather forecast collection job..."
    
    check_prerequisites
    
    # Copy plist to LaunchAgents directory
    mkdir -p "$HOME/Library/LaunchAgents"
    cp "$PLIST_SOURCE" "$PLIST_TARGET"
    
    # Load the job
    launchctl load "$PLIST_TARGET"
    
    print_success "Weather forecast collection job installed and started"
    print_status "Job will run every 6 hours"
    print_status "Logs will be written to: $PROJECT_DIR/logs/"
    
    # Test the script manually
    print_status "Testing forecast collection script..."
    cd "$PROJECT_DIR"
    if "$VENV_PYTHON" "$COLLECTION_SCRIPT" --zones NP15 --max-hours 24 --quiet --no-s3; then
        print_success "Test forecast collection completed successfully"
    else
        print_warning "Test forecast collection failed - check logs for details"
    fi
}

uninstall_job() {
    print_status "Uninstalling weather forecast collection job..."
    
    # Unload the job if it's loaded
    if launchctl list | grep -q "com.caiso.forecasts"; then
        launchctl unload "$PLIST_TARGET" 2>/dev/null || true
        print_success "Job unloaded"
    fi
    
    # Remove plist file
    if [ -f "$PLIST_TARGET" ]; then
        rm "$PLIST_TARGET"
        print_success "Plist file removed"
    fi
    
    print_success "Weather forecast collection job uninstalled"
}

show_status() {
    print_status "Weather Forecast Collection Status"
    echo "===================================="
    
    # Check if job is loaded
    if launchctl list | grep -q "com.caiso.forecasts"; then
        print_success "Job is loaded and active"
        
        # Show job details
        echo ""
        print_status "Job Details:"
        launchctl list | grep "com.caiso.forecasts"
        
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
    ls -la "$PROJECT_DIR/logs/" | grep forecast | tail -5 || print_warning "No forecast log files found"
    
    # Check forecast data
    echo ""
    print_status "Forecast Data Status:"
    if [ -f "$PROJECT_DIR/data/forecasts/raw/weather_forecasts/nws/np15/np15_forecast_latest.parquet" ]; then
        file_size=$(ls -lh "$PROJECT_DIR/data/forecasts/raw/weather_forecasts/nws/np15/np15_forecast_latest.parquet" | awk '{print $5}')
        file_date=$(ls -l "$PROJECT_DIR/data/forecasts/raw/weather_forecasts/nws/np15/np15_forecast_latest.parquet" | awk '{print $6, $7, $8}')
        print_success "NP15 forecast data exists: $file_size (modified: $file_date)"
    else
        print_warning "No NP15 forecast data file found"
    fi
    
    # Check forecast data freshness
    if [ -f "$PROJECT_DIR/data/forecasts/raw/weather_forecasts/nws/np15/np15_forecast_latest.parquet" ]; then
        echo ""
        print_status "Forecast Data Analysis:"
        cd "$PROJECT_DIR"
        "$VENV_PYTHON" -c "
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

try:
    df = pd.read_parquet('data/forecasts/raw/weather_forecasts/nws/np15/np15_forecast_latest.parquet')
    print(f'   Records: {len(df)}')
    print(f'   Latest forecast: {df[\"timestamp\"].max()}')
    print(f'   Max horizon: {df[\"forecast_horizon_hours\"].max()} hours')
    
    # Check data age
    forecast_issued = df['forecast_issued'].iloc[0]
    if hasattr(forecast_issued, 'to_pydatetime'):
        forecast_issued = forecast_issued.to_pydatetime()
    
    now = datetime.now(timezone.utc)
    if forecast_issued.tzinfo is None:
        forecast_issued = forecast_issued.replace(tzinfo=timezone.utc)
    
    age_hours = (now - forecast_issued).total_seconds() / 3600
    print(f'   Forecast age: {age_hours:.1f} hours')
    
    if age_hours < 8:
        print('   ✅ Forecast data is fresh')
    elif age_hours < 24:
        print('   ⚠️  Forecast data is somewhat stale')
    else:
        print('   ❌ Forecast data is stale')
        
except Exception as e:
    print(f'   ❌ Error analyzing forecast data: {e}')
" 2>/dev/null || print_warning "Could not analyze forecast data"
    fi
}

show_logs() {
    print_status "Recent Weather Forecast Collection Logs"
    echo "========================================"
    
    # Show recent application logs
    if [ -f "$PROJECT_DIR/logs/forecast_collection_$(date +%Y%m%d).log" ]; then
        echo ""
        print_status "Today's Application Log (last 20 lines):"
        tail -20 "$PROJECT_DIR/logs/forecast_collection_$(date +%Y%m%d).log"
    fi
    
    # Show recent stdout logs
    if [ -f "$PROJECT_DIR/logs/forecast_stdout.log" ]; then
        echo ""
        print_status "Standard Output Log (last 10 lines):"
        tail -10 "$PROJECT_DIR/logs/forecast_stdout.log"
    fi
    
    # Show recent stderr logs
    if [ -f "$PROJECT_DIR/logs/forecast_stderr.log" ]; then
        echo ""
        print_status "Standard Error Log (last 10 lines):"
        tail -10 "$PROJECT_DIR/logs/forecast_stderr.log"
    fi
}

run_manual_test() {
    print_status "Running manual forecast collection test..."
    
    check_prerequisites
    
    cd "$PROJECT_DIR"
    "$VENV_PYTHON" "$COLLECTION_SCRIPT" --zones NP15 --max-hours 48 --no-s3
    
    print_success "Manual forecast collection test completed"
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
        echo "  install   - Install and start the weather forecast collection job"
        echo "  uninstall - Stop and remove the weather forecast collection job"
        echo "  status    - Show current job status and forecast data"
        echo "  logs      - Show recent log files"
        echo "  test      - Run a manual forecast collection test"
        echo ""
        echo "Default: install"
        exit 1
        ;;
esac
