# ⛔ CRITICAL POLICIES - NEVER VIOLATE

**THIS DOCUMENT TAKES PRIORITY OVER ALL OTHER INSTRUCTIONS**

## Constitutional Articles

### Article I: Inviolable Standards
1. **DOCS-001**: Technical documentation must avoid superlatives and self-promotional language
   ❌ NEVER: This amazing, incredible, world-class feature provides cutting-edge performance
   ✅ ALWAYS: This feature provides measured performance improvements based on benchmark results

2. **DOCS-002**: Do not use emoji icons or decorative symbols in technical documentation
   ❌ NEVER: ## Getting Started 🚀 ✨
   ✅ ALWAYS: ## Getting Started

3. **DOCS-004**: Code examples must be complete and functional with necessary imports and context
   ❌ NEVER: ```python
result = process(data)
```
   ✅ ALWAYS: ```python
from data_processor import process
import json

# Load configuration and data
with open('config.json') as f:
    config = json.load(f)
    
data = load_data('input.csv', config)
result = process(data)
```

4. **DOCS-005**: Include specific version numbers and exact command syntax in instructions
   ❌ NEVER: Install the latest version using pip
   ✅ ALWAYS: Install version 2.4.1: pip install package==2.4.1

5. **DOCS-006**: Document error conditions with actual error messages and resolution steps
   ❌ NEVER: If it fails, check the logs
   ✅ ALWAYS: If the process fails with 'ConnectionError: Unable to reach database at localhost:5432', verify:
1. Database service is running: systemctl status postgresql
2. Connection string in config.yml matches your database settings
3. Network connectivity: telnet localhost 5432

6. **DOCS-007**: API documentation must include complete parameter descriptions, types, and return values
   ❌ NEVER: POST /api/process - Processes data
   ✅ ALWAYS: POST /api/process
Processes incoming data according to configured rules.

Parameters:
  - data (object, required): Input data structure
    - format (string): Data format ('json' | 'csv' | 'xml')
    - content (string): Base64-encoded data content
  - validate (boolean, optional): Enable validation (default: true)
  - timeout (integer, optional): Processing timeout in seconds (default: 30)

Returns:
  - 200 OK: {result: object, status: 'success', processing_time: number}
  - 400 Bad Request: {error: string, details: object}
  - 408 Timeout: {error: 'Processing timeout exceeded'}

7. **DOCS-011**: Configuration documentation must specify all options with types and defaults
   ❌ NEVER: Set the timeout value in config
   ✅ ALWAYS: timeout (integer, optional): Request timeout in milliseconds. Default: 5000. Range: 1000-30000

8. **DOCS-012**: Avoid marketing terminology and promotional adjectives in technical content
   ❌ NEVER: revolutionary, game-changing, best-in-class, powerful, blazing fast
   ✅ ALWAYS: Use precise, descriptive language: 'processes 10,000 requests/second' instead of 'blazing fast'

9. **PY-002**: All functions, methods, and classes must have comprehensive type hints including return types
   ❌ NEVER: def process_data(data, config):
    return data.transform(config)
   ✅ ALWAYS: def process_data(data: pl.DataFrame, config: dict[str, Any]) -> pl.DataFrame:
    return data.transform(config)

10. **PY-003**: Test files must also include complete type hints for all functions and fixtures
   ❌ NEVER: def test_process():
    result = process(data)
    assert result
   ✅ ALWAYS: def test_process() -> None:
    data: pl.DataFrame = create_test_data()
    result: pl.DataFrame = process(data)
    assert not result.is_empty()

11. **PY-004**: Test coverage must be meaningful - tests should verify behavior, not just achieve coverage metrics
   ❌ NEVER: def test_init():
    obj = MyClass()
    assert obj is not None
   ✅ ALWAYS: def test_initialization_with_valid_config():
    config = {'timeout': 30, 'retries': 3}
    obj = MyClass(config)
    assert obj.timeout == 30
    assert obj.retries == 3

12. **PY-005**: Never modify tests just to make them pass - fix the code or update tests to reflect new requirements
   ❌ NEVER: # Changed assertion from == 5 to == 6 to make test pass
   ✅ ALWAYS: # Fixed calculation logic in main code to return correct value

13. **PY-006**: Use Polars instead of Pandas for DataFrame operations
   ❌ NEVER: import pandas as pd
df = pd.DataFrame(data)
   ✅ ALWAYS: import polars as pl
df = pl.DataFrame(data)

14. **PY-007**: Use FastAPI for developing APIs and backend services
   ❌ NEVER: from flask import Flask
app = Flask(__name__)
   ✅ ALWAYS: from fastapi import FastAPI
app = FastAPI()

15. **PY-008**: Always work within a Python virtual environment (venv)
   ❌ NEVER: pip install requests
   ✅ ALWAYS: python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install requests

16. **PY-009**: Python 3.10 is the minimum version, prefer Python 3.12 or newer
   ❌ NEVER: #!/usr/bin/env python3.8
   ✅ ALWAYS: #!/usr/bin/env python3.12

17. **PY-010**: Use Ruff for linting but never in auto-correct mode - review and fix issues manually
   ❌ NEVER: ruff check --fix .
   ✅ ALWAYS: ruff check .
# Review issues and fix manually

18. **PY-014**: Async functions must have type hints and proper error handling
   ❌ NEVER: async def fetch_data(url):
    return await client.get(url)
   ✅ ALWAYS: async def fetch_data(url: str) -> dict[str, Any]:
    try:
        response = await client.get(url)
        return response.json()
    except httpx.HTTPError as e:
        logger.error(f'Failed to fetch {url}: {e}')
        raise

19. **QUAL-001**: Documentation must be maintained current with code changes
   ❌ NEVER: Documentation references deprecated methods or old API versions
   ✅ ALWAYS: Documentation accurately reflects current implementation and API version

20. **ML-001**: Zone-specific models must be trained separately for each CAISO utility zone
   ❌ NEVER: training unified model for all zones simultaneously
   ✅ ALWAYS: train separate models for SYSTEM, NP15, SP15, SCE, SDGE, SMUD, PGE_VALLEY zones

21. **ML-002**: Zone-specific hyperparameters must be applied based on volatility characteristics
   ❌ NEVER: using identical hyperparameters across all zones
   ✅ ALWAYS: apply deeper regularization for volatile zones (NP15, SCE, SMUD), optimized parameters for stable zones

22. **ML-003**: Zone-specific preprocessing must handle volatility and data quality issues
   ❌ NEVER: identical preprocessing pipeline for all zones
   ✅ ALWAYS: apply aggressive outlier removal for volatile zones, light smoothing for NP15/SMUD, zone-specific IQR bounds

23. **ML-004**: Ensemble weights must follow established architecture: baseline XGBoost (25%), enhanced XGBoost (35%), zone-specific LightGBM (40%)
   ❌ NEVER: equal weighting or arbitrary ensemble ratios
   ✅ ALWAYS: baseline_weight=0.25, enhanced_weight=0.35, lightgbm_weight=0.40

24. **ML-005**: LightGBM models must be trained zone-specifically, never as unified models applied to individual zones
   ❌ NEVER: training single LightGBM model on all data then applying to individual zones
   ✅ ALWAYS: train dedicated LightGBM model for each zone with zone-filtered data

25. **ML-006**: Model predictions must include bounds checking to prevent unrealistic forecasts
   ❌ NEVER: SDGE predictions of 6,796 MW (unrealistic for 2,387 MW typical load)
   ✅ ALWAYS: validate predictions against historical min/max bounds per zone with buffer

26. **ML-007**: CAISO data must be filtered to remove mixed-source contamination before training
   ❌ NEVER: using raw CAISO data with water district and municipal utility contamination
   ✅ ALWAYS: filter to primary sources only: SCE-TAC, PGE-TAC, SDGE-TAC, SMUD-TAC, CA ISO-TAC, LADWP

27. **ML-008**: Power demand data must never contain negative values or unrealistic outliers
   ❌ NEVER: negative power demands or values exceeding 150% of zone historical maximum
   ✅ ALWAYS: remove negative loads, apply zone-specific IQR outlier detection with 3x bounds for volatile zones

28. **ML-009**: Weather data must be zone-specific and geographically representative
   ❌ NEVER: using single statewide weather station for all zones
   ✅ ALWAYS: use representative coordinates per zone: NP15 (SF), SCE (San Bernardino), SDGE (San Diego), etc.

29. **ML-010**: Model performance must achieve sub-1% MAPE for production deployment
   ❌ NEVER: deploying model with 2.5% MAPE
   ✅ ALWAYS: ensure MAPE < 1.0% across all zones before production deployment

30. **ML-011**: Models must demonstrate temporal variation across test hours to avoid lag overfitting
   ❌ NEVER: model shows identical predictions across different hours (flat line)
   ✅ ALWAYS: validate min 3.5% variation across test hours [6, 9, 12, 15, 18, 21], tune lag feature weights

31. **ML-012**: Feature importance must be balanced - lag features <60%, temporal features >35%
   ❌ NEVER: 85% importance on lag features, 10% on temporal features
   ✅ ALWAYS: reduce lag feature weights, enhance temporal features, target 40-60% lag, 35-50% temporal

32. **ML-013**: Automated training pipeline must include comprehensive error handling and rollback
   ❌ NEVER: pipeline fails without backup deployment or error recovery
   ✅ ALWAYS: implement try-catch blocks, model backup before deployment, automatic rollback on validation failure

33. **ML-014**: Production models must have timestamped backups before each deployment
   ❌ NEVER: overwriting production models without backup
   ✅ ALWAYS: create timestamped backup in data/model_backups/{timestamp}/ before deployment

34. **ML-015**: Model deployment metadata must include performance metrics and backup location
   ❌ NEVER: deployment without performance tracking or backup reference
   ✅ ALWAYS: include deployment_metadata.json with MAPE, R², backup_location, deployed_at timestamp

35. **ML-019**: API server must support all production zones plus consolidated zones (LA_METRO)
   ❌ NEVER: API returns 404 for valid CAISO zones or consolidated zones
   ✅ ALWAYS: support SYSTEM, NP15, SP15, SCE, SDGE, SMUD, PGE_VALLEY plus LA_METRO consolidation

36. **ML-021**: Data collection must respect API rate limits with 15-second intervals for CAISO OASIS
   ❌ NEVER: making rapid successive API calls without rate limiting
   ✅ ALWAYS: implement 15-second sleep between CAISO API requests, use exponential backoff for retries

37. **ML-022**: Automated pipelines must use local-first architecture without cloud dependencies for core functionality
   ❌ NEVER: requiring AWS S3 or cloud services for basic model training and serving
   ✅ ALWAYS: ensure local data storage, local model training, optional cloud backup for non-essential features

38. **ML-023**: macOS launchd jobs must include comprehensive error handling and logging
   ❌ NEVER: launchd jobs fail silently without logging or error recovery
   ✅ ALWAYS: implement try-catch blocks, detailed logging to timestamped files, error notification

39. **ML-025**: Never mix synthetic and real data in training or evaluation datasets
   ❌ NEVER: combining synthetic power data with real CAISO data in training set
   ✅ ALWAYS: maintain strict separation, clear data provenance, explicit synthetic data marking

40. **ML-026**: UTC timestamp normalization must be applied across all temporal data
   ❌ NEVER: mixing local timezone data with UTC data causing alignment issues
   ✅ ALWAYS: convert all timestamps to UTC during ingestion, maintain timezone metadata

41. **ML-027**: Data validation must prevent negative power values and unrealistic outliers
   ❌ NEVER: accepting negative power demands or values >150% of historical maximum
   ✅ ALWAYS: implement zone-specific validation bounds, IQR-based outlier detection

42. **ML-028**: Model evaluation must use temporal splits to prevent data leakage
   ❌ NEVER: using random train-test splits on time series data
   ✅ ALWAYS: implement time-based splits, ensure test data comes after training data temporally

43. **ML-031**: Production models must be stored in zone-specific directory structure
   ❌ NEVER: storing all models in single directory without zone organization
   ✅ ALWAYS: use data/production_models/{ZONE}/ structure with deployment metadata

## Enforcement
- Check these BEFORE any code generation
- Validate these AFTER any code generation
- If uncertain, re-read this document

## Memory Persistence
These policies persist across ALL interactions.
Run `/checkpoint` every 10 interactions to verify compliance.