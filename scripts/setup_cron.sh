#!/bin/bash
"""
Setup cron jobs for automated ML pipeline

This script configures cron jobs to run the ML pipeline on schedule:
- Every 15 minutes: Fresh predictions
- Every 6 hours: Data ingestion
- Daily at 2 AM: Model retraining
"""

PROJECT_DIR="/Users/bran/Work/model-power-nowcast"
PYTHON_ENV="$PROJECT_DIR/.venv/bin/python"
PIPELINE_SCRIPT="$PROJECT_DIR/scripts/automated_pipeline.py"
LOG_DIR="$PROJECT_DIR/logs"

# Create log directory
mkdir -p "$LOG_DIR"

# Create cron configuration
CRON_CONFIG=$(cat << EOF
# Power Demand Forecasting ML Pipeline
# Generated on $(date)

# Fresh predictions every 15 minutes
*/15 * * * * cd $PROJECT_DIR && $PYTHON_ENV $PIPELINE_SCRIPT --mode predictions >> $LOG_DIR/predictions.log 2>&1

# Data ingestion every 6 hours
0 */6 * * * cd $PROJECT_DIR && $PYTHON_ENV $PIPELINE_SCRIPT --mode ingest >> $LOG_DIR/ingest.log 2>&1

# Model retraining daily at 2 AM
0 2 * * * cd $PROJECT_DIR && $PYTHON_ENV $PIPELINE_SCRIPT --mode retrain >> $LOG_DIR/retrain.log 2>&1

# Full pipeline run daily at 3 AM (backup)
0 3 * * * cd $PROJECT_DIR && $PYTHON_ENV $PIPELINE_SCRIPT >> $LOG_DIR/full_pipeline.log 2>&1

# Log rotation weekly
0 0 * * 0 find $LOG_DIR -name "*.log" -mtime +7 -delete

EOF
)

echo "Setting up cron jobs for ML pipeline..."
echo "$CRON_CONFIG"

# Install cron jobs
echo "$CRON_CONFIG" | crontab -

echo "✅ Cron jobs installed successfully!"
echo ""
echo "To view current cron jobs:"
echo "  crontab -l"
echo ""
echo "To view logs:"
echo "  tail -f $LOG_DIR/predictions.log"
echo "  tail -f $LOG_DIR/retrain.log"
echo ""
echo "To remove cron jobs:"
echo "  crontab -r"
