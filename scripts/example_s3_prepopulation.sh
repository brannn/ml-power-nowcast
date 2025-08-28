#!/bin/bash
# Example script for S3 data pre-population
# 
# This script demonstrates how to pre-populate your S3 bucket with historical
# power and weather data from your local macOS environment.

set -e  # Exit on any error

# Configuration
BUCKET_NAME="ml-power-nowcast-dev-mlflow-im9godhe"  # Replace with your bucket
YEARS=3  # Years of historical data to fetch

echo "🚀 ML Power Nowcast - S3 Data Pre-population Example"
echo "📦 Target bucket: s3://$BUCKET_NAME"
echo "📅 Years of data: $YEARS"
echo ""

# Check if AWS credentials are configured
echo "🔐 Checking AWS credentials..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS credentials not configured!"
    echo "Run: aws configure"
    echo "Or set environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
    exit 1
fi

echo "✅ AWS credentials configured"
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not detected. Activating..."
    source .venv/bin/activate
fi

echo "🐍 Python environment: $VIRTUAL_ENV"
echo ""

# List existing data first
echo "📋 Checking existing data in S3..."
python3 scripts/prepopulate_s3_data.py --bucket "$BUCKET_NAME" --list-only
echo ""

# Pre-populate data
echo "🔄 Starting data pre-population..."
python3 scripts/prepopulate_s3_data.py \
    --bucket "$BUCKET_NAME" \
    --years "$YEARS" \
    --noaa-token "${NOAA_API_TOKEN:-}"

echo ""
echo "✅ Data pre-population complete!"
echo ""
echo "💡 Usage tips:"
echo "   - Set NOAA_API_TOKEN environment variable for better weather data"
echo "   - Use --force flag to overwrite existing data"
echo "   - Use --power-only or --weather-only for partial updates"
echo "   - Check data with: make list-s3-data BUCKET=$BUCKET_NAME"
