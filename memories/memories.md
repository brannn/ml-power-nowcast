# LA_METRO Discrepancy Investigation - System Analysis

**Investigation Date**: 2025-09-03  
**Issue**: Dashboard LA_METRO zone showing inconsistent predictions vs individual model predictions  
**Status**: Root cause identified, solution pending

## Executive Summary

Investigated a critical discrepancy in the LA_METRO zone predictions where dashboard values differed significantly from expected model outputs. The investigation revealed a fundamental flaw in the API server's composite zone calculation logic that violates ML-005 policy requirements for zone-specific modeling.

## System Architecture Understanding

### Dashboard Frontend (Next.js)
- **Location**: `/dashboard/src/`
- **Framework**: Next.js 15.5.2 with Turbopack
- **Port**: 3000
- **Regional Provider**: `/dashboard/src/components/RegionalProvider.tsx`
- **Zone Definitions**: Lines 68-77 define LA_METRO as composite zone
- **API Integration**: Direct fetch calls to FastAPI backend at `http://localhost:8001`

### API Backend (FastAPI) 
- **Location**: `/src/api/regional_api_server.py`
- **Framework**: FastAPI with uvicorn
- **Port**: 8001
- **Models**: Loads production models from `/data/production_models/{ZONE}/`
- **Forecaster**: Uses `RealtimeForecaster` from `/src/prediction/realtime_forecaster.py`

### Zone Architecture Discovery

#### Available API Zones
```
NP15, ZP26, SP15, SDGE, SCE, PGE_BAY, PGE_VALLEY, SMUD, STATEWIDE
```

#### LA_METRO Composition
- **Definition**: "Combined LA metropolitan area (SCE + LADWP territories)"
- **Components**: SCE (Southern California Edison) + SP15 (LADWP Territory)
- **Load Weight**: 0.68 (theoretical)
- **Climate Region**: "Mediterranean/semi-arid"
- **Virtual Zone**: Not a real CAISO zone, exists only in dashboard frontend

## Investigation Process & Findings

### Phase 1: Service Verification
- ✅ Dashboard running on http://localhost:3000
- ✅ API server running on http://0.0.0.0:8001
- ✅ Both services operational with loaded models

### Phase 2: Data Collection
**Dashboard LA_METRO Display:**
- Current Demand: 23,695 MW
- Next Hour Prediction: 21,287 MW
- Change: -10.2% (decrease expected)

**Individual Zone API Predictions:**
- SCE: 18,696 MW current → 19,631 MW predicted
- SP15: 4,999 MW current → 5,249 MW predicted
- **Combined Expected**: 23,695 MW current → 24,880 MW predicted (+5.0%)

**Discrepancy Identified:**
- Current load matches: 23,695 MW ✅
- Prediction discrepancy: 21,287 MW vs 24,880 MW = **3,593 MW error (15.2%)**

### Phase 3: Root Cause Analysis

#### API Endpoint Testing
- ❌ `/predict/LA_METRO` (GET): Returns 404 Not Found
- ✅ `/weather/LA_METRO` (GET): Returns valid data
- ✅ `/trend/LA_METRO` (GET): Returns valid data  
- ✅ `/predict` (POST with LA_METRO zone): Returns predictions

#### Dashboard Data Flow Discovery
Dashboard calls:
1. `POST /predict?model_id=xgboost` with LA_METRO zone data
2. `GET /weather/LA_METRO`
3. `GET /trend/LA_METRO`

#### Flawed Scaling Logic Identified
**Location**: `src/api/regional_api_server.py:556-573`

```python
# For LA_METRO, scale the SCE prediction to account for combined load
if zone == "LA_METRO":
    # Get current loads for scaling
    sce_current = 0.0
    sp15_current = 0.0
    
    # ... load current values ...
    
    combined_current = sce_current + sp15_current
    
    if sce_current > 0 and combined_current > 0:
        # Scale prediction by the ratio of combined load to SCE load
        scale_factor = combined_current / sce_current
        predicted_load = predicted_load * scale_factor
```

**Problems with this approach:**
1. **Uses only SCE model prediction** (ignores SP15 model entirely)
2. **Applies current load ratio scaling** instead of model-based predictions
3. **Violates ML-005 policy**: "Zone-specific models must be trained separately"
4. **Creates inconsistent predictions** compared to individual zone models

### Phase 4: Verification
**API Logs Confirmed:**
```
INFO:__main__:Using scaled LA_METRO ML prediction: SCE(16914.38671875) × scale(1.267) = 21437.3115592456 MW
```

**Calculation Verification:**
- Scale Factor: 23,695 / 18,696 = 1.267
- But uses different SCE prediction (16,914 MW vs 19,631 MW from individual endpoint)
- Suggests different forecasting contexts or caching issues

## Technical Impact Assessment

### Policy Violations
- **ML-005**: Zone-specific models must be trained separately for each CAISO utility zone
- **ML-006**: Model predictions must include bounds checking to prevent unrealistic forecasts
- **QUAL-001**: Documentation must be maintained current with code changes

### System Reliability Issues
1. **Prediction Inconsistency**: 15.2% error in composite zone predictions
2. **Model Architecture Violation**: Scaling single model instead of ensemble approach
3. **Data Integrity**: Different endpoints returning different predictions for same model
4. **User Trust**: Dashboard showing incorrect forecasts for major metropolitan area

### Business Impact
- LA_METRO represents significant portion of California's power grid
- Inaccurate predictions affect grid planning and resource allocation
- Potential financial implications for power trading and capacity planning

## System Dependencies Discovered

### Frontend Dependencies
- React 18+ with Next.js 15.5.2
- Regional context management via RegionalProvider
- Real-time data fetching every 5 minutes
- Theme and unit system management

### Backend Dependencies
- FastAPI with CORS middleware
- Real-time forecasting pipeline
- Production model loading from filesystem
- Zone-specific weather data integration
- Caching and data freshness tracking

### Model Infrastructure
- XGBoost and LightGBM models per zone
- Ensemble approach with baseline/enhanced variants
- Feature engineering with weather and temporal data
- Zone-specific hyperparameters and preprocessing

## Recommended Solution Approach

### Immediate Fix (API Server)
1. **Replace scaling logic** with proper model aggregation
2. **Sum individual predictions**: SCE prediction + SP15 prediction  
3. **Maintain confidence intervals** from individual models
4. **Add logging** for debugging composite calculations

### Long-term Architecture Improvement
1. **Implement dedicated LA_METRO model** trained on combined historical data
2. **Create composite zone framework** for other virtual zones
3. **Add validation layer** comparing composite vs individual predictions
4. **Implement caching consistency** across endpoints

### Code Location for Fix
- **Primary**: `/src/api/regional_api_server.py:556-573`
- **Secondary**: Prediction aggregation logic throughout API server
- **Testing**: Add unit tests for composite zone calculations

## Files Modified During Investigation
- None (investigation only)

## Key Learning: System Complexity
This investigation revealed the complexity of the power forecasting system with multiple layers:
- Dashboard presentation layer with virtual zones
- API transformation layer with zone-specific logic  
- Model serving layer with individual zone predictions
- Data layer with real-time weather integration

The discrepancy was caused by inconsistency between these layers, specifically in the API transformation logic for composite zones.