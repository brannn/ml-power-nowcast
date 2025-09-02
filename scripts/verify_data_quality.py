#!/usr/bin/env python3
"""
CAISO Historical Data Quality Verification Script

This script performs comprehensive quality checks on the collected 5-year CAISO data:
- Data completeness and coverage
- Zone distribution and mapping
- Temporal consistency and gaps
- Load value ranges and outliers
- Weather data alignment
- Data types and schema validation

Usage:
    python scripts/verify_data_quality.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

def load_and_inspect_data():
    """Load all collected data files and perform basic inspection."""
    print("🔍 CAISO 5-YEAR DATA QUALITY VERIFICATION")
    print("=" * 60)
    
    data_dir = Path("data/historical")
    
    # Load power data
    print("\n📊 LOADING POWER DATA...")
    power_file = data_dir / "caiso_5year_full.parquet"
    if not power_file.exists():
        print(f"❌ Power data file not found: {power_file}")
        return None, None, None
    
    power_df = pd.read_parquet(power_file)
    print(f"✅ Loaded power data: {len(power_df):,} records")
    print(f"   File size: {power_file.stat().st_size / (1024**2):.1f} MB")
    
    # Load system data
    print("\n🏛️  LOADING SYSTEM DATA...")
    system_file = data_dir / "caiso_5year_system.parquet"
    if system_file.exists():
        system_df = pd.read_parquet(system_file)
        print(f"✅ Loaded system data: {len(system_df):,} records")
        print(f"   File size: {system_file.stat().st_size / (1024**2):.1f} MB")
    else:
        print("⚠️  System data file not found")
        system_df = None
    
    # Load weather data
    print("\n🌤️  LOADING WEATHER DATA...")
    weather_file = data_dir / "caiso_5year_weather.parquet"
    if weather_file.exists():
        weather_df = pd.read_parquet(weather_file)
        print(f"✅ Loaded weather data: {len(weather_df):,} records")
        print(f"   File size: {weather_file.stat().st_size / (1024**2):.1f} MB")
    else:
        print("⚠️  Weather data file not found")
        weather_df = None
    
    return power_df, system_df, weather_df

def analyze_power_data(power_df):
    """Comprehensive analysis of power data quality."""
    print("\n📈 POWER DATA ANALYSIS")
    print("=" * 40)
    
    # Basic info
    print(f"📊 Dataset Overview:")
    print(f"   Records: {len(power_df):,}")
    print(f"   Columns: {list(power_df.columns)}")
    print(f"   Memory usage: {power_df.memory_usage(deep=True).sum() / (1024**2):.1f} MB")
    
    # Data types
    print(f"\n🔧 Data Types:")
    for col, dtype in power_df.dtypes.items():
        print(f"   {col}: {dtype}")
    
    # Temporal coverage
    print(f"\n📅 Temporal Coverage:")
    power_df['timestamp'] = pd.to_datetime(power_df['timestamp'])
    start_date = power_df['timestamp'].min()
    end_date = power_df['timestamp'].max()
    duration = (end_date - start_date).days
    print(f"   Start: {start_date}")
    print(f"   End: {end_date}")
    print(f"   Duration: {duration} days ({duration/365.25:.1f} years)")
    
    # Zone analysis
    print(f"\n🗺️  Zone Analysis:")
    zone_counts = power_df['zone'].value_counts().sort_values(ascending=False)
    for zone, count in zone_counts.items():
        percentage = (count / len(power_df)) * 100
        print(f"   {zone}: {count:,} records ({percentage:.1f}%)")
    
    # Load statistics
    print(f"\n⚡ Load Statistics:")
    load_stats = power_df['load'].describe()
    for stat, value in load_stats.items():
        if stat in ['mean', 'std', 'min', 'max']:
            print(f"   {stat.capitalize()}: {value:,.1f} MW")
        else:
            print(f"   {stat}: {value:,.1f} MW")
    
    # Check for missing values
    print(f"\n🔍 Missing Values:")
    missing = power_df.isnull().sum()
    for col, count in missing.items():
        if count > 0:
            percentage = (count / len(power_df)) * 100
            print(f"   {col}: {count:,} ({percentage:.2f}%)")
        else:
            print(f"   {col}: None ✅")
    
    # Check for duplicates
    print(f"\n🔄 Duplicate Analysis:")
    total_duplicates = power_df.duplicated().sum()
    timestamp_zone_duplicates = power_df.duplicated(subset=['timestamp', 'zone']).sum()
    print(f"   Total duplicates: {total_duplicates:,}")
    print(f"   Timestamp+Zone duplicates: {timestamp_zone_duplicates:,}")
    
    # Temporal gaps analysis
    print(f"\n⏰ Temporal Gaps Analysis:")
    for zone in zone_counts.index[:3]:  # Check top 3 zones
        zone_data = power_df[power_df['zone'] == zone].sort_values('timestamp')
        time_diffs = zone_data['timestamp'].diff().dropna()
        expected_interval = pd.Timedelta(minutes=5)  # CAISO 5-minute data
        
        gaps = time_diffs[time_diffs > expected_interval * 1.5]  # Allow 50% tolerance
        print(f"   {zone}: {len(gaps)} gaps > 7.5 minutes")
        
        if len(gaps) > 0:
            largest_gap = gaps.max()
            print(f"     Largest gap: {largest_gap}")

def analyze_system_data(system_df):
    """Analyze system-wide data quality."""
    if system_df is None:
        print("\n🏛️  SYSTEM DATA: Not available")
        return
    
    print("\n🏛️  SYSTEM DATA ANALYSIS")
    print("=" * 40)
    
    print(f"📊 System Overview:")
    print(f"   Records: {len(system_df):,}")
    print(f"   Columns: {list(system_df.columns)}")
    
    # Temporal coverage
    system_df['timestamp'] = pd.to_datetime(system_df['timestamp'])
    start_date = system_df['timestamp'].min()
    end_date = system_df['timestamp'].max()
    print(f"   Date range: {start_date} to {end_date}")
    
    # Load statistics
    print(f"\n⚡ System Load Statistics:")
    load_stats = system_df['load'].describe()
    for stat, value in load_stats.items():
        if stat in ['mean', 'std', 'min', 'max']:
            print(f"   {stat.capitalize()}: {value:,.1f} MW")
    
    # Check for reasonable values (California typically 20-50 GW)
    reasonable_min = 15000  # 15 GW
    reasonable_max = 60000  # 60 GW
    outliers = system_df[(system_df['load'] < reasonable_min) | (system_df['load'] > reasonable_max)]
    print(f"\n🚨 Load Outliers (< {reasonable_min/1000:.0f} GW or > {reasonable_max/1000:.0f} GW):")
    print(f"   Count: {len(outliers):,} ({len(outliers)/len(system_df)*100:.2f}%)")

def analyze_weather_data(weather_df):
    """Analyze weather data quality and coverage."""
    if weather_df is None:
        print("\n🌤️  WEATHER DATA: Not available")
        return
    
    print("\n🌤️  WEATHER DATA ANALYSIS")
    print("=" * 40)
    
    print(f"📊 Weather Overview:")
    print(f"   Records: {len(weather_df):,}")
    print(f"   Columns: {list(weather_df.columns)}")
    
    # Zone coverage
    if 'zone' in weather_df.columns:
        print(f"\n🗺️  Weather Zone Coverage:")
        zone_counts = weather_df['zone'].value_counts().sort_values(ascending=False)
        for zone, count in zone_counts.items():
            print(f"   {zone}: {count:,} records")
    
    # Temperature analysis
    if 'temp' in weather_df.columns:
        print(f"\n🌡️  Temperature Statistics:")
        temp_stats = weather_df['temp'].describe()
        for stat, value in temp_stats.items():
            if not pd.isna(value):
                print(f"   {stat.capitalize()}: {value:.1f}°C")
    
    # Missing values
    print(f"\n🔍 Weather Missing Values:")
    missing = weather_df.isnull().sum()
    for col, count in missing.items():
        if count > 0:
            percentage = (count / len(weather_df)) * 100
            print(f"   {col}: {count:,} ({percentage:.2f}%)")

def generate_summary_report(power_df, system_df, weather_df):
    """Generate final summary report."""
    print("\n📋 FINAL SUMMARY REPORT")
    print("=" * 60)
    
    # Overall data quality score
    quality_score = 100
    issues = []
    
    # Check power data completeness
    if power_df is not None:
        missing_power = power_df.isnull().sum().sum()
        if missing_power > 0:
            quality_score -= 10
            issues.append(f"Power data has {missing_power:,} missing values")
        
        # Check temporal coverage
        duration_years = (power_df['timestamp'].max() - power_df['timestamp'].min()).days / 365.25
        if duration_years < 4.5:
            quality_score -= 15
            issues.append(f"Only {duration_years:.1f} years of data (expected ~5 years)")
        
        # Check zone coverage
        expected_zones = {'SYSTEM', 'NP15', 'SCE', 'SMUD', 'PGE_VALLEY', 'SP15', 'SDGE'}
        actual_zones = set(power_df['zone'].unique())
        missing_zones = expected_zones - actual_zones
        if missing_zones:
            quality_score -= 20
            issues.append(f"Missing zones: {missing_zones}")
    
    # Check system data
    if system_df is None:
        quality_score -= 5
        issues.append("System data not available")
    
    # Check weather data
    if weather_df is None:
        quality_score -= 10
        issues.append("Weather data not available")
    
    print(f"🎯 Overall Data Quality Score: {quality_score}/100")
    
    if quality_score >= 90:
        print("✅ EXCELLENT - Data is ready for ML training")
    elif quality_score >= 80:
        print("✅ GOOD - Data is suitable for ML training with minor issues")
    elif quality_score >= 70:
        print("⚠️  FAIR - Data has some issues but may be usable")
    else:
        print("❌ POOR - Data has significant issues requiring attention")
    
    if issues:
        print(f"\n🚨 Issues Found:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    else:
        print(f"\n🎉 No significant issues found!")
    
    # Next steps
    print(f"\n📋 RECOMMENDED NEXT STEPS:")
    if quality_score >= 80:
        print("   1. ✅ Proceed with feature engineering")
        print("   2. ✅ Train ML models (XGBoost, LSTM)")
        print("   3. ✅ Evaluate model performance")
        print("   4. ✅ Deploy to production dashboard")
    else:
        print("   1. 🔧 Address data quality issues")
        print("   2. 🔄 Re-run data collection if needed")
        print("   3. 🧹 Clean and validate data")
        print("   4. ✅ Proceed with ML pipeline")

def main():
    """Main verification function."""
    # Load data
    power_df, system_df, weather_df = load_and_inspect_data()
    
    if power_df is None:
        print("❌ Cannot proceed without power data")
        return
    
    # Analyze each dataset
    analyze_power_data(power_df)
    analyze_system_data(system_df)
    analyze_weather_data(weather_df)
    
    # Generate summary
    generate_summary_report(power_df, system_df, weather_df)

if __name__ == "__main__":
    main()
