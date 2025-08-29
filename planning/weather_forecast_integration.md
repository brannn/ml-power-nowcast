# Weather Forecast Integration Implementation Plan

## 🎯 **Executive Summary**

This plan outlines the integration of weather forecast data into our ML power demand prediction pipeline. Currently, our models use only historical/current weather data, missing the critical predictive capability that weather forecasts provide. Adding forecast data is expected to improve model accuracy by **5-15% MAPE reduction** for 6-24 hour predictions.

## 📊 **Current State Analysis**

### ✅ **What We Have:**
- **Historical weather data**: Meteostat API integration
- **Zone-specific weather**: Data for each CAISO zone
- **Weather features**: Temperature, humidity, wind speed, interactions
- **Feature engineering**: Cooling/heating degree days, temperature squared

### ❌ **What We're Missing:**
- **Weather forecasts**: No look-ahead weather data
- **Predictive capability**: Models are reactive, not predictive
- **Weather uncertainty**: No forecast confidence metrics
- **Weather change rates**: No trend analysis

## 🌤️ **Free Weather Forecast APIs**

### **1. National Weather Service (NWS) - RECOMMENDED PRIMARY**
- **URL**: `https://api.weather.gov`
- **Authentication**: None required
- **Rate Limits**: Reasonable for our use case
- **Coverage**: Excellent for US/California
- **Data Quality**: High (official government source)
- **Forecast Horizon**: Up to 7 days hourly
- **Key Endpoints**:
  - `/points/{lat},{lon}` - Get grid coordinates
  - `/gridpoints/{office}/{gridX},{gridY}/forecast/hourly` - Hourly forecasts

### **2. Open-Meteo - RECOMMENDED SECONDARY**
- **URL**: `https://api.open-meteo.com`
- **Authentication**: None required
- **Rate Limits**: 10,000 requests/day free
- **Coverage**: Global
- **Data Quality**: Good (ensemble forecasts)
- **Forecast Horizon**: Up to 16 days
- **Key Features**: Ensemble forecasts, uncertainty data

### **3. WeatherAPI (Free Tier) - BACKUP**
- **URL**: `https://api.weatherapi.com`
- **Authentication**: API key (free registration)
- **Rate Limits**: 1M calls/month free
- **Coverage**: Global
- **Forecast Horizon**: Up to 10 days

## 🏗️ **Implementation Architecture**

### **Phase 1: Core Infrastructure (Week 1-2)**

#### **1.1 New Data Collection Module**
```
src/ingest/pull_weather_forecasts.py
├── fetch_nws_forecasts()
├── fetch_open_meteo_forecasts()
├── fetch_weatherapi_forecasts()
├── aggregate_zone_forecasts()
└── validate_forecast_data()
```

#### **1.2 Enhanced Feature Engineering**
```
src/features/build_forecast_features.py
├── create_temperature_forecast_features()
├── create_weather_change_features()
├── create_forecast_uncertainty_features()
└── create_weather_event_features()
```

#### **1.3 Data Storage Updates**
```
S3 Structure:
├── raw/weather_forecasts/
│   ├── nws/
│   │   ├── {zone}_{date}_hourly.parquet
│   ├── open_meteo/
│   │   ├── {zone}_{date}_forecast.parquet
└── processed/weather_forecasts/
    ├── combined_forecasts_{date}.parquet
```

### **Phase 2: Feature Development (Week 3-4)**

#### **2.1 Core Forecast Features**
- `temp_forecast_1h`, `temp_forecast_6h`, `temp_forecast_12h`, `temp_forecast_24h`
- `humidity_forecast_6h`, `humidity_forecast_12h`
- `wind_forecast_6h`, `wind_forecast_12h`
- `cooling_degree_forecast_6h`, `heating_degree_forecast_6h`

#### **2.2 Advanced Features**
- `temp_change_rate_6h` - Rate of temperature change
- `weather_volatility_6h` - Forecast uncertainty measure
- `extreme_temp_probability` - Probability of extreme temperatures
- `weather_pattern_stability` - How stable the forecast is

#### **2.3 Weather Event Detection**
- `heat_wave_incoming` - Heat wave detection (3+ days >35°C)
- `cold_snap_incoming` - Cold snap detection (3+ days <5°C)
- `rapid_temp_change` - >10°C change in 6 hours

### **Phase 3: Model Integration (Week 5-6)**

#### **3.1 Enhanced XGBoost Model**
```python
enhanced_features = [
    # Existing features
    'temp_c', 'humidity', 'wind_speed', 'hour', 'day_of_week',
    'temp_c_squared', 'cooling_degree_days', 'heating_degree_days',
    'load_lag_1h', 'load_lag_24h',
    
    # New forecast features
    'temp_forecast_6h', 'temp_forecast_12h', 'temp_forecast_24h',
    'cooling_forecast_6h', 'heating_forecast_6h',
    'temp_change_rate_6h', 'weather_volatility_6h',
    'heat_wave_incoming', 'cold_snap_incoming'
]
```

#### **3.2 Enhanced LSTM Model**
- **Temporal forecast sequences**: Use forecast time series as input
- **Multi-horizon outputs**: Predict multiple time steps ahead
- **Uncertainty estimation**: Output prediction intervals

#### **3.3 Weather-Aware Ensemble**
- **Forecast confidence weighting**: Weight models based on weather certainty
- **Weather regime detection**: Different models for different weather patterns
- **Adaptive uncertainty**: Wider intervals during uncertain weather

## 📋 **Detailed Implementation Steps**

### **Step 1: NWS API Integration**

#### **1.1 Grid Point Resolution**
```python
def get_nws_grid_point(latitude: float, longitude: float) -> dict:
    """Get NWS grid coordinates for a location."""
    url = f"https://api.weather.gov/points/{latitude},{longitude}"
    response = requests.get(url)
    return response.json()
```

#### **1.2 Hourly Forecast Retrieval**
```python
def fetch_nws_hourly_forecast(office: str, grid_x: int, grid_y: int) -> pd.DataFrame:
    """Fetch hourly weather forecast from NWS."""
    url = f"https://api.weather.gov/gridpoints/{office}/{grid_x},{grid_y}/forecast/hourly"
    response = requests.get(url)
    data = response.json()
    
    forecasts = []
    for period in data['properties']['periods']:
        forecasts.append({
            'timestamp': pd.to_datetime(period['startTime']),
            'temp_c': (period['temperature'] - 32) * 5/9,  # F to C
            'humidity': period.get('relativeHumidity', {}).get('value'),
            'wind_speed': period.get('windSpeed', '0 mph').split()[0],
            'forecast_source': 'nws'
        })
    
    return pd.DataFrame(forecasts)
```

### **Step 2: Open-Meteo Integration**

```python
def fetch_open_meteo_forecast(latitude: float, longitude: float, hours: int = 48) -> pd.DataFrame:
    """Fetch weather forecast from Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        'latitude': latitude,
        'longitude': longitude,
        'hourly': 'temperature_2m,relative_humidity_2m,wind_speed_10m',
        'forecast_days': min(hours // 24 + 1, 7),
        'timezone': 'America/Los_Angeles'
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    
    df = pd.DataFrame({
        'timestamp': pd.to_datetime(data['hourly']['time']),
        'temp_c': data['hourly']['temperature_2m'],
        'humidity': data['hourly']['relative_humidity_2m'],
        'wind_speed': data['hourly']['wind_speed_10m'],
        'forecast_source': 'open_meteo'
    })
    
    return df.head(hours)
```

### **Step 3: Feature Engineering**

```python
def create_forecast_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create weather forecast features."""
    
    # Temperature forecasts at different horizons
    for horizon in [1, 6, 12, 24]:
        df[f'temp_forecast_{horizon}h'] = df['temp_c'].shift(-horizon)
        df[f'cooling_forecast_{horizon}h'] = np.maximum(
            df[f'temp_forecast_{horizon}h'] - 18, 0
        )
        df[f'heating_forecast_{horizon}h'] = np.maximum(
            18 - df[f'temp_forecast_{horizon}h'], 0
        )
    
    # Weather change rates
    df['temp_change_rate_6h'] = (df['temp_forecast_6h'] - df['temp_c']) / 6
    df['humidity_change_rate_6h'] = (df['humidity_forecast_6h'] - df['humidity']) / 6
    
    # Weather volatility (rolling standard deviation of forecasts)
    df['weather_volatility_6h'] = df['temp_forecast_6h'].rolling(6).std()
    
    # Extreme weather detection
    df['heat_wave_incoming'] = (
        (df['temp_forecast_24h'] > 35) & 
        (df['temp_forecast_48h'] > 35) & 
        (df['temp_forecast_72h'] > 35)
    ).astype(int)
    
    df['cold_snap_incoming'] = (
        (df['temp_forecast_24h'] < 5) & 
        (df['temp_forecast_48h'] < 5) & 
        (df['temp_forecast_72h'] < 5)
    ).astype(int)
    
    return df
```

## 📅 **Implementation Timeline**

### **Week 1: Infrastructure Setup**
- [ ] Create `pull_weather_forecasts.py` module
- [ ] Implement NWS API integration
- [ ] Set up S3 storage structure for forecasts
- [ ] Create basic data validation functions

### **Week 2: Data Collection**
- [ ] Implement Open-Meteo API integration
- [ ] Create zone-specific forecast collection
- [ ] Set up automated forecast data pipeline
- [ ] Test data quality and coverage

### **Week 3: Feature Engineering**
- [ ] Create `build_forecast_features.py` module
- [ ] Implement core forecast features
- [ ] Add weather change rate calculations
- [ ] Create extreme weather detection

### **Week 4: Advanced Features**
- [ ] Implement forecast uncertainty features
- [ ] Add weather pattern stability metrics
- [ ] Create weather event detection algorithms
- [ ] Validate feature quality

### **Week 5: Model Integration**
- [ ] Update XGBoost model with forecast features
- [ ] Enhance LSTM model for temporal forecasts
- [ ] Create weather-aware ensemble model
- [ ] Implement forecast confidence weighting

### **Week 6: Testing & Validation**
- [ ] Backtest models with historical forecast data
- [ ] Measure accuracy improvements
- [ ] Validate forecast feature importance
- [ ] Optimize model hyperparameters

## 🎯 **Success Metrics**

### **Primary Metrics:**
- **MAPE Reduction**: Target 5-15% improvement in 6-24h forecasts
- **Peak Prediction**: Improved accuracy during temperature extremes
- **Confidence Intervals**: More accurate uncertainty estimates

### **Secondary Metrics:**
- **Data Coverage**: >95% forecast data availability
- **API Reliability**: <1% failed forecast requests
- **Feature Importance**: Weather forecasts in top 10 features

## 🚨 **Risk Mitigation**

### **API Reliability:**
- **Multiple sources**: NWS + Open-Meteo redundancy
- **Graceful degradation**: Fall back to historical patterns
- **Caching strategy**: Store recent forecasts locally

### **Data Quality:**
- **Validation checks**: Range checks, missing data detection
- **Outlier detection**: Flag unrealistic forecast values
- **Source comparison**: Cross-validate between APIs

### **Model Stability:**
- **Gradual rollout**: Test with subset of zones first
- **A/B testing**: Compare forecast vs non-forecast models
- **Monitoring**: Track model performance degradation

## 🔄 **Maintenance Plan**

### **Daily:**
- Automated forecast data collection
- Data quality monitoring
- API health checks

### **Weekly:**
- Model performance review
- Forecast accuracy assessment
- Feature importance analysis

### **Monthly:**
- API source evaluation
- Model retraining with new data
- Performance optimization

## 💡 **Future Enhancements**

### **Phase 4: Advanced Analytics (Month 2-3)**
- **Ensemble weather forecasts**: Combine multiple sources
- **Forecast error learning**: Learn from forecast vs actual differences
- **Weather regime classification**: Different models for different patterns
- **Extreme event prediction**: Specialized models for heat waves/cold snaps

### **Phase 5: Real-time Integration (Month 3-4)**
- **Live forecast updates**: Real-time forecast ingestion
- **Dynamic model selection**: Choose models based on weather conditions
- **Forecast-driven alerts**: Notify operators of predicted demand spikes
- **Interactive forecast visualization**: Dashboard showing weather impact

---

**Next Steps**: Begin with Phase 1 implementation, starting with NWS API integration for core CAISO zones.
