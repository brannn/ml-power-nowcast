#!/usr/bin/env python3
"""
Comprehensive test runner for ML Power Nowcast pipeline.

Runs all tests with coverage reporting and generates a summary of
test results for recent training work and evaluation/registry functionality.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import pytest


def run_pytest_with_coverage(test_paths: List[str]) -> Tuple[int, str]:
    """
    Run pytest with coverage reporting.
    
    Args:
        test_paths: List of test file/directory paths
        
    Returns:
        Tuple of (return_code, output)
    """
    cmd = [
        sys.executable, "-m", "pytest",
        "--verbose",
        "--tb=short",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        *test_paths
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "Tests timed out after 5 minutes"
    except Exception as e:
        return 1, f"Error running tests: {e}"


def run_specific_test_suite(suite_name: str, test_path: str) -> Dict[str, any]:
    """
    Run a specific test suite and return results.
    
    Args:
        suite_name: Name of the test suite
        test_path: Path to test file/directory
        
    Returns:
        Dictionary with test results
    """
    print(f"\n{'='*60}")
    print(f"Running {suite_name} Tests")
    print(f"{'='*60}")
    
    if not Path(test_path).exists():
        return {
            "suite": suite_name,
            "status": "SKIPPED",
            "reason": f"Test path {test_path} does not exist",
            "passed": 0,
            "failed": 0,
            "total": 0
        }
    
    return_code, output = run_pytest_with_coverage([test_path])
    
    # Parse pytest output for test counts
    lines = output.split('\n')
    passed = failed = total = 0
    
    for line in lines:
        if "passed" in line and "failed" in line:
            # Parse line like "5 passed, 2 failed in 1.23s"
            parts = line.split()
            for i, part in enumerate(parts):
                if part == "passed,":
                    passed = int(parts[i-1])
                elif part == "failed":
                    failed = int(parts[i-1])
        elif line.strip().endswith("passed"):
            # Parse line like "10 passed in 1.23s"
            parts = line.split()
            for i, part in enumerate(parts):
                if part == "passed":
                    passed = int(parts[i-1])
    
    total = passed + failed
    status = "PASSED" if return_code == 0 else "FAILED"
    
    print(output)
    
    return {
        "suite": suite_name,
        "status": status,
        "return_code": return_code,
        "passed": passed,
        "failed": failed,
        "total": total,
        "output": output
    }


def test_feature_engineering() -> Dict[str, any]:
    """Test feature engineering pipeline (recent training work)."""
    return run_specific_test_suite(
        "Feature Engineering",
        "tests/test_features/test_build_features.py"
    )


def test_model_evaluation() -> Dict[str, any]:
    """Test model evaluation and registry (Sections 11-12)."""
    return run_specific_test_suite(
        "Model Evaluation & Registry",
        "tests/test_models/test_evaluate.py"
    )


def test_data_ingestion() -> Dict[str, any]:
    """Test data ingestion components."""
    return run_specific_test_suite(
        "Data Ingestion",
        "tests/test_ingest/"
    )


def run_integration_tests() -> Dict[str, any]:
    """Run end-to-end integration tests."""
    print(f"\n{'='*60}")
    print("Running Integration Tests")
    print(f"{'='*60}")
    
    try:
        # Test complete pipeline with sample data
        from src.features.build_features import build_features
        from src.models.evaluate import evaluate_model_performance
        import tempfile
        import pandas as pd
        import numpy as np
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample data
            dates = pd.date_range('2024-01-01', periods=168, freq='h')
            
            power_df = pd.DataFrame({
                'timestamp': dates,
                'load': 1000 + 200 * np.sin(2 * np.pi * np.arange(168) / 24) + np.random.normal(0, 50, 168),
                'region': 'TEST',
                'data_source': 'synthetic'
            })
            
            weather_df = pd.DataFrame({
                'timestamp': dates,
                'temp_c': 15 + 10 * np.sin(2 * np.pi * np.arange(168) / 24) + np.random.normal(0, 2, 168),
                'humidity': 60 + 20 * np.sin(2 * np.pi * np.arange(168) / 48) + np.random.normal(0, 5, 168),
                'wind_speed': 5 + 3 * np.random.random(168),
                'region': 'TEST',
                'data_source': 'synthetic'
            })
            
            # Save sample data
            power_path = Path(temp_dir) / "power.parquet"
            weather_path = Path(temp_dir) / "weather.parquet"
            features_path = Path(temp_dir) / "features.parquet"
            
            power_df.to_parquet(power_path, index=False)
            weather_df.to_parquet(weather_path, index=False)
            
            # Test feature building
            features_df, target_col = build_features(
                power_data_path=str(power_path),
                weather_data_path=str(weather_path),
                horizon=1,
                lags=[1, 2, 6],
                rolling_windows=[3, 6],
                output_path=str(features_path)
            )
            
            # Test evaluation functions
            y_true = np.random.normal(1000, 200, 100)
            y_pred = y_true + np.random.normal(0, 50, 100)
            
            metrics = evaluate_model_performance(y_true, y_pred, "integration_test")
            
            print("✅ Integration test passed:")
            print(f"  - Features created: {len([col for col in features_df.columns if col not in ['timestamp', target_col]])}")
            print(f"  - Samples processed: {len(features_df)}")
            print(f"  - Evaluation metrics: {len(metrics)}")
            print(f"  - Test MAE: {metrics['integration_test_mae']:.2f}")
            
            return {
                "suite": "Integration Tests",
                "status": "PASSED",
                "return_code": 0,
                "passed": 1,
                "failed": 0,
                "total": 1,
                "details": {
                    "features_created": len([col for col in features_df.columns if col not in ['timestamp', target_col]]),
                    "samples_processed": len(features_df),
                    "metrics_calculated": len(metrics)
                }
            }
            
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return {
            "suite": "Integration Tests",
            "status": "FAILED",
            "return_code": 1,
            "passed": 0,
            "failed": 1,
            "total": 1,
            "error": str(e)
        }


def generate_test_summary(results: List[Dict[str, any]]) -> None:
    """Generate comprehensive test summary."""
    print(f"\n{'='*80}")
    print("ML POWER NOWCAST - COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*80}")
    
    total_passed = sum(r.get("passed", 0) for r in results)
    total_failed = sum(r.get("failed", 0) for r in results)
    total_tests = total_passed + total_failed
    
    print(f"\nOverall Results:")
    print(f"  Total Tests: {total_tests}")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    print(f"  Success Rate: {(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "  Success Rate: N/A")
    
    print(f"\nTest Suite Breakdown:")
    print(f"{'Suite':<30} {'Status':<10} {'Passed':<8} {'Failed':<8} {'Total':<8}")
    print("-" * 70)
    
    for result in results:
        suite = result["suite"][:29]
        status = result["status"]
        passed = result.get("passed", 0)
        failed = result.get("failed", 0)
        total = result.get("total", 0)
        
        status_icon = "✅" if status == "PASSED" else "❌" if status == "FAILED" else "⏭️"
        print(f"{suite:<30} {status_icon} {status:<8} {passed:<8} {failed:<8} {total:<8}")
    
    # Recent work focus areas
    print(f"\n{'='*60}")
    print("RECENT WORK VALIDATION")
    print(f"{'='*60}")
    
    feature_result = next((r for r in results if "Feature" in r["suite"]), None)
    eval_result = next((r for r in results if "Evaluation" in r["suite"]), None)
    integration_result = next((r for r in results if "Integration" in r["suite"]), None)
    
    print("\n🔧 Training Pipeline (Last Night's Work):")
    if feature_result:
        print(f"  Feature Engineering: {feature_result['status']} ({feature_result.get('passed', 0)}/{feature_result.get('total', 0)} tests)")
    else:
        print("  Feature Engineering: NOT TESTED")
    
    print("\n📊 Evaluation & Registry (Sections 11-12):")
    if eval_result:
        print(f"  Model Evaluation: {eval_result['status']} ({eval_result.get('passed', 0)}/{eval_result.get('total', 0)} tests)")
    else:
        print("  Model Evaluation: NOT TESTED")
    
    print("\n🔗 End-to-End Integration:")
    if integration_result:
        print(f"  Pipeline Integration: {integration_result['status']}")
        if "details" in integration_result:
            details = integration_result["details"]
            print(f"    - Features Created: {details.get('features_created', 'N/A')}")
            print(f"    - Samples Processed: {details.get('samples_processed', 'N/A')}")
            print(f"    - Metrics Calculated: {details.get('metrics_calculated', 'N/A')}")
    else:
        print("  Pipeline Integration: NOT TESTED")
    
    # Recommendations
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")
    
    if total_failed > 0:
        print("❌ Some tests failed. Priority actions:")
        for result in results:
            if result["status"] == "FAILED":
                print(f"  - Fix {result['suite']} ({result.get('failed', 0)} failures)")
    else:
        print("✅ All tests passed! Pipeline is ready for:")
        print("  - Production deployment")
        print("  - Real data processing with S3 pre-population")
        print("  - Model training with zone-based weather data")
        print("  - MLflow model registry workflows")


def main() -> None:
    """Main test runner function."""
    print("🚀 ML Power Nowcast - Comprehensive Test Suite")
    print("Testing recent training work and Sections 11-12 implementation")
    
    # Run all test suites
    results = []
    
    # Test recent training work
    results.append(test_feature_engineering())
    
    # Test Sections 11-12 (evaluation and registry)
    results.append(test_model_evaluation())
    
    # Test data ingestion (existing)
    results.append(test_data_ingestion())
    
    # Run integration tests
    results.append(run_integration_tests())
    
    # Generate comprehensive summary
    generate_test_summary(results)
    
    # Exit with appropriate code
    failed_suites = [r for r in results if r["status"] == "FAILED"]
    sys.exit(len(failed_suites))


if __name__ == "__main__":
    main()
