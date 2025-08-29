#!/usr/bin/env python3
"""
Continuous Training Data Pipeline Status Checker

This script provides a comprehensive overview of the continuous training
data pipeline, showing how historical and incremental data flow together
for seamless ML model updates.

Usage:
    python scripts/check_continuous_training_status.py
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import json

def check_dataset_status():
    """Check status of all datasets in the pipeline."""
    
    print("📊 CONTINUOUS TRAINING DATA PIPELINE STATUS")
    print("=" * 60)
    
    datasets = {
        "Historical (5-year)": "data/historical/caiso_5year_full.parquet",
        "Incremental (recent)": "data/incremental/caiso_recent.parquet", 
        "Master (merged)": "data/master/caiso_master.parquet",
        "California-only": "data/master/caiso_california_only.parquet"
    }
    
    for name, path in datasets.items():
        print(f"\n🔍 {name}:")
        file_path = Path(path)
        
        if not file_path.exists():
            print(f"   ❌ File not found: {path}")
            continue
        
        try:
            df = pd.read_parquet(file_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            file_size = file_path.stat().st_size / (1024**2)  # MB
            
            print(f"   ✅ Records: {len(df):,}")
            print(f"   📅 Date range: {df.timestamp.min()} to {df.timestamp.max()}")
            print(f"   💾 File size: {file_size:.1f} MB")
            
            # Zone breakdown for California data
            if 'zone' in df.columns:
                ca_zones = df[df['zone'].notnull()]
                if len(ca_zones) > 0:
                    zone_counts = ca_zones['zone'].value_counts()
                    print(f"   🗺️  CA Zones: {dict(zone_counts)}")
                    
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")


def check_metadata():
    """Check dataset metadata if available."""
    
    metadata_file = Path("data/master/dataset_metadata.json")
    if metadata_file.exists():
        print(f"\n📋 MASTER DATASET METADATA:")
        print("-" * 30)
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            print(f"   Created: {metadata.get('created', 'Unknown')}")
            print(f"   Total records: {metadata.get('total_records', 0):,}")
            print(f"   California records: {metadata.get('california_records', 0):,}")
            print(f"   Date range: {metadata.get('date_range_start', 'Unknown')} to {metadata.get('date_range_end', 'Unknown')}")
            print(f"   File size: {metadata.get('file_size_mb', 0):.1f} MB")
            
        except Exception as e:
            print(f"   ❌ Error reading metadata: {e}")


def check_data_freshness():
    """Check how fresh the data is."""
    
    print(f"\n⏰ DATA FRESHNESS:")
    print("-" * 20)
    
    now = datetime.now()
    
    # Check incremental data freshness
    inc_file = Path("data/incremental/caiso_recent.parquet")
    if inc_file.exists():
        try:
            df = pd.read_parquet(inc_file, columns=['timestamp'])
            latest_data = pd.to_datetime(df['timestamp']).max()
            age = now - latest_data.to_pydatetime().replace(tzinfo=None)
            
            print(f"   Latest incremental data: {latest_data}")
            print(f"   Data age: {age}")
            
            if age < timedelta(hours=1):
                print(f"   ✅ Data is fresh (< 1 hour old)")
            elif age < timedelta(hours=6):
                print(f"   ⚠️  Data is somewhat stale ({age.total_seconds()/3600:.1f} hours old)")
            else:
                print(f"   ❌ Data is stale (> 6 hours old)")
                
        except Exception as e:
            print(f"   ❌ Error checking freshness: {e}")
    else:
        print(f"   ❌ No incremental data found")


def check_scheduled_job():
    """Check if the scheduled collection job is running."""
    
    print(f"\n🔄 SCHEDULED COLLECTION STATUS:")
    print("-" * 35)
    
    import subprocess
    
    try:
        # Check if launchd job is loaded
        result = subprocess.run(
            ["launchctl", "list"], 
            capture_output=True, 
            text=True
        )
        
        if "com.caiso.incremental" in result.stdout:
            print(f"   ✅ Scheduled job is active")
            
            # Get job details
            lines = result.stdout.split('\n')
            for line in lines:
                if "com.caiso.incremental" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        pid = parts[0]
                        status = parts[1] 
                        print(f"   📊 Job PID: {pid}, Status: {status}")
        else:
            print(f"   ❌ Scheduled job not found")
            
    except Exception as e:
        print(f"   ❌ Error checking scheduled job: {e}")


def check_pipeline_health():
    """Overall pipeline health assessment."""
    
    print(f"\n🏥 PIPELINE HEALTH ASSESSMENT:")
    print("-" * 35)
    
    health_score = 100
    issues = []
    
    # Check if master dataset exists and is recent
    master_file = Path("data/master/caiso_master.parquet")
    if not master_file.exists():
        health_score -= 30
        issues.append("Master dataset missing")
    else:
        # Check if master dataset is recent
        mod_time = datetime.fromtimestamp(master_file.stat().st_mtime)
        age = datetime.now() - mod_time
        if age > timedelta(hours=2):
            health_score -= 15
            issues.append(f"Master dataset not updated recently ({age})")
    
    # Check if incremental collection is working
    inc_file = Path("data/incremental/caiso_recent.parquet")
    if not inc_file.exists():
        health_score -= 25
        issues.append("Incremental data missing")
    else:
        try:
            df = pd.read_parquet(inc_file, columns=['timestamp'])
            latest = pd.to_datetime(df['timestamp']).max()
            age = datetime.now() - latest.to_pydatetime().replace(tzinfo=None)
            if age > timedelta(hours=3):
                health_score -= 20
                issues.append(f"Incremental data is stale ({age})")
        except:
            health_score -= 15
            issues.append("Cannot read incremental data")
    
    # Check if California-only dataset exists
    ca_file = Path("data/master/caiso_california_only.parquet")
    if not ca_file.exists():
        health_score -= 15
        issues.append("California-only dataset missing")
    
    # Health assessment
    print(f"   🎯 Health Score: {health_score}/100")
    
    if health_score >= 90:
        print(f"   ✅ EXCELLENT - Pipeline is healthy and ready for ML training")
    elif health_score >= 75:
        print(f"   ✅ GOOD - Pipeline is working with minor issues")
    elif health_score >= 60:
        print(f"   ⚠️  FAIR - Pipeline has some issues that should be addressed")
    else:
        print(f"   ❌ POOR - Pipeline has significant issues requiring attention")
    
    if issues:
        print(f"\n   🚨 Issues found:")
        for i, issue in enumerate(issues, 1):
            print(f"      {i}. {issue}")
    
    return health_score >= 75


def show_next_steps():
    """Show recommended next steps based on pipeline status."""
    
    print(f"\n📋 RECOMMENDED NEXT STEPS:")
    print("-" * 30)
    
    ca_file = Path("data/master/caiso_california_only.parquet")
    if ca_file.exists():
        print(f"   1. ✅ Feature Engineering: Create time-based and weather features")
        print(f"   2. ✅ Model Training: Train XGBoost and LSTM models")
        print(f"   3. ✅ Model Evaluation: Validate performance on recent data")
        print(f"   4. ✅ Continuous Training: Set up model retraining pipeline")
        print(f"   5. ✅ Production Deployment: Deploy models for real-time forecasting")
        
        print(f"\n   🎯 Ready for ML Pipeline!")
        print(f"   📁 Training data: {ca_file}")
        
        # Show data volume
        try:
            df = pd.read_parquet(ca_file, columns=['timestamp'])
            print(f"   📊 Training records: {len(df):,}")
            print(f"   📅 Training span: {pd.to_datetime(df['timestamp']).min()} to {pd.to_datetime(df['timestamp']).max()}")
        except:
            pass
    else:
        print(f"   1. 🔧 Fix data pipeline issues")
        print(f"   2. 🔄 Run dataset merge: python scripts/merge_datasets.py")
        print(f"   3. ✅ Verify data quality")
        print(f"   4. 🚀 Proceed with ML pipeline")


def main():
    """Main status checking function."""
    
    check_dataset_status()
    check_metadata()
    check_data_freshness()
    check_scheduled_job()
    
    pipeline_healthy = check_pipeline_health()
    show_next_steps()
    
    print(f"\n" + "=" * 60)
    if pipeline_healthy:
        print(f"🎉 CONTINUOUS TRAINING PIPELINE IS READY!")
        print(f"   Your system will automatically collect fresh CAISO data every 30 minutes")
        print(f"   and merge it into the master dataset for continuous ML model updates.")
    else:
        print(f"⚠️  PIPELINE NEEDS ATTENTION")
        print(f"   Please address the issues above before proceeding with ML training.")


if __name__ == "__main__":
    main()
