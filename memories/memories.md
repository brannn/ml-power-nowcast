# LA_METRO Discrepancy Investigation - System Analysis

Investigation Date: 2025-09-03  
Issue: Dashboard LA_METRO zone showing inconsistent predictions vs individual model predictions  
Status: Root cause identified, solution pending

## Executive Summary

This investigation addressed a critical discrepancy in LA_METRO zone predictions where dashboard values differed significantly from expected model outputs. The analysis revealed a fundamental flaw in the API server's composite zone calculation logic that violates ML-005 policy requirements for zone-specific modeling.

## System Architecture Understanding

The power forecasting system consists of a Next.js dashboard frontend communicating with a FastAPI backend server. The dashboard frontend is located in `/dashboard/src/` and runs on port 3000 using Next.js 15.5.2 with Turbopack. Zone definitions are managed through the RegionalProvider component at `/dashboard/src/components/RegionalProvider.tsx`, where lines 68-77 specifically define LA_METRO as a composite zone. The frontend integrates with the backend through direct fetch calls to the FastAPI server at `http://localhost:8001`.

The API backend operates from `/src/api/regional_api_server.py` using FastAPI with uvicorn on port 8001. The system loads production models from `/data/production_models/{ZONE}/` directories and utilizes the RealtimeForecaster from `/src/prediction/realtime_forecaster.py` for generating predictions.

The API server supports nine distinct zones: NP15, ZP26, SP15, SDGE, SCE, PGE_BAY, PGE_VALLEY, SMUD, and STATEWIDE. The LA_METRO zone represents a composite virtual zone that combines the Southern California Edison (SCE) and LADWP Territory (SP15) service areas. This virtual zone has a theoretical load weight of 0.68, operates in a Mediterranean/semi-arid climate region, and exists only within the dashboard frontend presentation layer rather than as an actual CAISO operational zone.

## Investigation Process and Findings

The investigation proceeded through systematic verification of system components and data collection phases. Initial service verification confirmed that both the dashboard and API server were operational, with the dashboard running on http://localhost:3000 and the API server running on http://0.0.0.0:8001. All production models loaded successfully across the supported zones.

Data collection revealed significant inconsistencies between dashboard displays and expected model outputs. The dashboard showed LA_METRO current demand at 23,695 MW with a next hour prediction of 21,287 MW, representing a 10.2% decrease. However, individual zone API predictions showed SCE at 18,696 MW current load with a predicted 19,631 MW, and SP15 at 4,999 MW current with a predicted 5,249 MW. The combined expected prediction should therefore be 24,880 MW, representing a 5.0% increase rather than a decrease.

This analysis identified a critical discrepancy where current load values matched perfectly at 23,695 MW, but predictions differed by 3,593 MW, representing a 15.2% error between dashboard display and proper model aggregation.

Root cause analysis involved comprehensive API endpoint testing and examination of the dashboard data flow. API endpoint testing revealed that while the GET request to `/predict/LA_METRO` returns a 404 Not Found error, the `/weather/LA_METRO` and `/trend/LA_METRO` endpoints return valid data. Most significantly, the POST request to `/predict` with LA_METRO zone data successfully returns predictions.

The dashboard data flow analysis showed that the frontend makes three specific API calls: a POST request to `/predict?model_id=xgboost` with LA_METRO zone data, a GET request to `/weather/LA_METRO`, and a GET request to `/trend/LA_METRO`. This sequence established that the dashboard receives LA_METRO prediction data through the standard prediction endpoint rather than a dedicated LA_METRO endpoint.

Investigation of the prediction logic revealed flawed scaling implementation in `src/api/regional_api_server.py` at lines 556-573. The current implementation scales SCE predictions by the ratio of combined current loads rather than properly aggregating individual model predictions:

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

This approach contains multiple critical flaws. The logic uses only the SCE model prediction while completely ignoring the SP15 model, applies current load ratio scaling instead of leveraging model-based predictions, violates the ML-005 policy requirement that zone-specific models must be trained separately, and creates inconsistent predictions compared to individual zone models.

Verification through API server logs confirmed the flawed approach. The logs showed "Using scaled LA_METRO ML prediction: SCE(16914.38671875) × scale(1.267) = 21437.3115592456 MW", which demonstrated that the system scales a single SCE prediction rather than aggregating both SCE and SP15 model outputs. Additionally, calculation verification revealed that while the scale factor computed correctly as 23,695 / 18,696 = 1.267, the system used a different SCE prediction value (16,914 MW versus 19,631 MW from the individual endpoint), suggesting inconsistencies in forecasting contexts or caching mechanisms.

## Technical Impact Assessment

The identified scaling logic creates multiple policy violations and system reliability issues. The implementation directly violates ML-005 requirements that zone-specific models must be trained separately for each CAISO utility zone. It also violates ML-006 requirements for model predictions to include bounds checking to prevent unrealistic forecasts, and QUAL-001 requirements that documentation must be maintained current with code changes.

System reliability issues include a 15.2% error in composite zone predictions, model architecture violations through scaling a single model instead of using an ensemble approach, data integrity problems with different endpoints returning different predictions for the same model, and potential user trust issues with the dashboard showing incorrect forecasts for a major metropolitan area.

The business impact extends beyond technical concerns. LA_METRO represents a significant portion of California's power grid, and inaccurate predictions affect grid planning and resource allocation. These discrepancies carry potential financial implications for power trading and capacity planning decisions that rely on accurate demand forecasting.

## System Dependencies

The frontend architecture relies on React 18+ with Next.js 15.5.2, regional context management through the RegionalProvider component, real-time data fetching every five minutes, and integrated theme and unit system management. The backend dependencies include FastAPI with CORS middleware, a real-time forecasting pipeline, production model loading from the filesystem, zone-specific weather data integration, and comprehensive caching with data freshness tracking.

The model infrastructure consists of XGBoost and LightGBM models for each zone, an ensemble approach with baseline and enhanced variants, feature engineering that incorporates weather and temporal data, and zone-specific hyperparameters and preprocessing logic. This infrastructure supports the zone-specific modeling requirements outlined in ML-005 policy but is not properly utilized for composite zone calculations.

## Recommended Solution Approach

The immediate fix requires replacing the scaling logic in the API server with proper model aggregation. The corrected approach should sum individual predictions from both SCE and SP15 models, maintain confidence intervals derived from individual models, and add comprehensive logging for debugging composite calculations. This change would align the system with ML-005 policy requirements and eliminate the 15.2% prediction error.

Long-term architecture improvements should include implementing a dedicated LA_METRO model trained on combined historical data, creating a comprehensive composite zone framework for other virtual zones, adding a validation layer that compares composite predictions against individual model aggregations, and implementing caching consistency mechanisms across all endpoints to prevent the observed discrepancies in prediction values.

The primary code location requiring modification is `/src/api/regional_api_server.py` at lines 556-573, with secondary changes needed throughout the API server for prediction aggregation logic consistency. A comprehensive testing framework should be added to validate composite zone calculations and ensure compliance with established ML policies.

## Key Learning Points

This investigation revealed the complexity of the power forecasting system with multiple interdependent layers including the dashboard presentation layer with virtual zones, the API transformation layer with zone-specific logic, the model serving layer with individual zone predictions, and the data layer with real-time weather integration. The discrepancy was caused by inconsistency between these layers, specifically in the API transformation logic for composite zones.

The investigation also highlighted the importance of maintaining architectural consistency across the system. While individual zone models properly implement ML-005 requirements for zone-specific training and prediction, the composite zone logic circumvented these requirements through inappropriate scaling mechanisms. Future development should ensure that all prediction logic, whether for individual or composite zones, adheres to established modeling policies and architectural patterns.