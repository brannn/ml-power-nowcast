# CAISO Historical Data Collection

This directory contains the script for collecting 5 years of real CAISO system load data.

## Quick Start

### 1. Dry Run (Recommended First)
```bash
# See the collection plan without actually collecting data
python scripts/collect_caiso_historical.py --dry-run
```

### 2. Full Collection (5 years: 2020-2025)
```bash
# Collect 5 years of power data only
python scripts/collect_caiso_historical.py

# Collect power + weather data for all zones
python scripts/collect_caiso_historical.py --collect-weather

# Collect both and upload to S3
python scripts/collect_caiso_historical.py --collect-weather --upload-s3
```

### 3. Custom Date Range
```bash
# Collect specific date range (power only)
python scripts/collect_caiso_historical.py --start-date 2022-01-01 --end-date 2024-12-31

# Collect last 2 years with weather data
python scripts/collect_caiso_historical.py --start-date 2023-08-28 --collect-weather
```

## What the Script Does

### ✅ **Data Collection:**
- **Real CAISO system load data** (not forecasts)
- **5-minute resolution** from CAISO OASIS API
- **7 granular zones**: SYSTEM, NP15, SCE, SMUD, PGE_VALLEY, SP15, SDGE
- **Proper scale**: 20-40 GW California system load
- **Optional weather data**: Zone-specific weather for all power zones

### ✅ **Rate Limiting:**
- **15-second delays** between API chunks
- **Exponential backoff** for rate limit errors
- **Reliable collection** without overwhelming the API

### ✅ **Progress Tracking:**
- **Real-time progress** updates
- **Time estimates** and completion status
- **Detailed logging** to `logs/` directory
- **Graceful interruption** handling

### ✅ **Data Output:**
- **Local files**: `data/historical/caiso_5year_*.parquet`
- **S3 upload**: Optional upload to S3 bucket
- **System data**: Separate file with SYSTEM zone only
- **Zone breakdown**: Statistics for all 7 zones
- **Weather data**: Zone-specific weather (if --collect-weather used)

## Weather Data Collection

### **🌤️ Zone-Specific Weather Data:**
The script can optionally collect weather data for all power zones using the `--collect-weather` flag. This provides **perfect weather-power zone alignment** for robust ML training.

### **📊 Weather Zones Covered:**
- **✅ SMUD (Sacramento)**: Valley heat patterns (38.58°N, -121.49°W)
- **✅ PGE_VALLEY (Modesto)**: Central Valley agriculture climate (37.64°N, -120.99°W)
- **✅ SP15 (Los Angeles)**: Urban heat island effects (34.05°N, -118.24°W)
- **✅ SCE (San Bernardino)**: Inland desert climate (34.15°N, -117.83°W)
- **✅ NP15 (San Francisco)**: Coastal fog and marine layer (37.77°N, -122.42°W)
- **✅ SDGE (San Diego)**: Mild coastal Mediterranean (32.72°N, -117.16°W)

### **🎯 Weather-Power Correlations:**
- **Temperature effects**: AC load in hot inland areas vs mild coastal zones
- **Seasonal patterns**: Different zones have distinct weather cycles
- **Geographic diversity**: Coast to inland, urban to agricultural
- **Climate zones**: Mediterranean coastal to hot semi-arid inland

### **📈 ML Model Benefits:**
- **Zone-specific features**: Temperature, humidity, wind for each power zone
- **Weather interactions**: Cross-zone weather pattern effects
- **Seasonal modeling**: Different zones peak at different times
- **Demand forecasting**: Weather-driven load predictions

## Expected Performance

### **5-Year Collection (2020-2025):**
- **Total Days**: 1,826 days
- **API Chunks**: ~131 chunks (14 days each)
- **Estimated Time**: ~33 minutes
- **Data Size**: ~50-100MB compressed
- **Records**: ~500K-1M records

### **System Requirements:**
- **Internet**: Stable connection for API calls
- **Disk Space**: ~200MB for 5 years of data
- **Memory**: ~1GB RAM during collection
- **Time**: 30-45 minutes uninterrupted

## Usage Examples

### Basic Collection
```bash
# Power data only (default)
python scripts/collect_caiso_historical.py

# Power + weather data for all zones
python scripts/collect_caiso_historical.py --collect-weather
```

### With S3 Upload
```bash
# Power data to S3
python scripts/collect_caiso_historical.py --upload-s3

# Power + weather data to S3
python scripts/collect_caiso_historical.py --collect-weather --upload-s3
```

### Custom Output Directory
```bash
# Save to custom directory
python scripts/collect_caiso_historical.py --output-dir data/caiso_historical
```

### Recent Data Only
```bash
# Last 1 year power data only
python scripts/collect_caiso_historical.py --start-date 2024-08-28

# Last 1 year with weather data
python scripts/collect_caiso_historical.py --start-date 2024-08-28 --collect-weather
```

## Output Files

### **Local Files:**
```
data/historical/
├── caiso_5year_full.parquet      # All zones and resources (power)
├── caiso_5year_system.parquet    # SYSTEM zone only (power)
└── caiso_5year_weather.parquet   # All zones weather (if --collect-weather)
```

### **S3 Files (if --upload-s3):**
```
s3://ml-power-nowcast-data-1756420517/
├── raw/power/caiso/historical_5year_YYYYMMDD.parquet
└── processed/power/caiso/system_5year_YYYYMMDD.parquet
```

### **Log Files:**
```
logs/
└── caiso_collection_YYYYMMDD_HHMMSS.log
```

## Data Quality

### **What You Get:**
- ✅ **Real actual load data** (not forecasts)
- ✅ **5-minute resolution** CAISO system data
- ✅ **Proper California scale** (20-40 GW)
- ✅ **7 granular zones** mapped correctly
- ✅ **5 years of history** for robust ML training
- ✅ **Zone-specific weather** (optional, perfectly aligned)

### **Data Validation:**
- ✅ **Load range check**: 15-50 GW (realistic CA range)
- ✅ **Date continuity**: No major gaps in timeline
- ✅ **Zone mapping**: SYSTEM zone properly identified
- ✅ **Record counts**: Expected ~100K records per year

## Troubleshooting

### **Rate Limiting (429 errors):**
- Script handles this automatically with exponential backoff
- If persistent, increase delays in `src/ingest/pull_power.py`

### **Network Issues:**
- Script will retry failed requests
- Use Ctrl+C to interrupt and restart later

### **Disk Space:**
- Monitor `data/historical/` directory size
- ~200MB needed for full 5-year collection

### **Memory Issues:**
- Collection processes data in chunks
- Should not exceed 1GB RAM usage

## Next Steps After Collection

1. **Verify data quality**: Check load ranges and date coverage
2. **Combine datasets**: Merge power and weather data by zone and timestamp
3. **Feature engineering**: Create weather-power interaction features
4. **Train ML models**: Use zone-specific and weather-enhanced features
5. **Model evaluation**: Test on recent data for validation
6. **Zone-specific modeling**: Train separate models for different climate zones

## Support

For issues or questions:
1. Check the log files in `logs/` directory
2. Review the script output for error messages
3. Verify AWS credentials for S3 upload (if used)
4. Ensure stable internet connection for API calls
