#!/usr/bin/env python3
"""
Model Quality Monitoring System

Continuously monitors production model performance and sends alerts
when quality degrades below acceptable thresholds.
"""

import logging
import json
import smtplib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import pandas as pd
import joblib

logger = logging.getLogger(__name__)


def check_model_quality(zone: str) -> Dict:
    """Check current model quality for a zone."""
    results = {
        'zone': zone,
        'timestamp': datetime.now().isoformat(),
        'status': 'healthy',
        'issues': []
    }
    
    # Check if model files exist
    model_dir = Path(f'data/production_models/{zone}')
    if not model_dir.exists():
        results['status'] = 'missing'
        results['issues'].append(f'Model directory not found: {model_dir}')
        return results
    
    # Check model file ages
    baseline_model = model_dir / 'baseline_model_current.joblib'
    enhanced_model = model_dir / 'enhanced_model_current.joblib'
    
    for model_path in [baseline_model, enhanced_model]:
        if not model_path.exists():
            results['issues'].append(f'Missing model: {model_path.name}')
            results['status'] = 'degraded'
            continue
            
        # Check if model is fresh (less than 8 hours old)
        model_age = datetime.now() - datetime.fromtimestamp(model_path.stat().st_mtime)
        if model_age > timedelta(hours=8):
            results['issues'].append(f'Stale model: {model_path.name} ({model_age})')
            results['status'] = 'degraded'
    
    # Load and validate model performance
    try:
        if baseline_model.exists():
            model = joblib.load(baseline_model)
            if hasattr(model, 'validation_metrics'):
                mape = model.validation_metrics.get('mape', 999.0)
                if mape > 2.0:
                    results['issues'].append(f'High MAPE: {mape:.2f}% (threshold: 2.0%)')
                    results['status'] = 'degraded'
                elif mape > 5.0:
                    results['issues'].append(f'Critical MAPE: {mape:.2f}%')
                    results['status'] = 'critical'
                    
                results['mape'] = mape
                results['r2'] = model.validation_metrics.get('r2', 0.0)
                
    except Exception as e:
        results['issues'].append(f'Model loading error: {str(e)}')
        results['status'] = 'error'
    
    return results


def monitor_all_zones() -> List[Dict]:
    """Monitor quality for all zones."""
    zones = ['SYSTEM', 'NP15', 'SCE', 'SDGE', 'SMUD', 'PGE_VALLEY', 'SP15']
    results = []
    
    for zone in zones:
        try:
            zone_result = check_model_quality(zone)
            results.append(zone_result)
            logger.info(f"Zone {zone}: {zone_result['status']} - {len(zone_result['issues'])} issues")
        except Exception as e:
            logger.error(f"Failed to check zone {zone}: {e}")
            results.append({
                'zone': zone,
                'status': 'error',
                'issues': [str(e)],
                'timestamp': datetime.now().isoformat()
            })
    
    return results


def generate_quality_report(results: List[Dict]) -> str:
    """Generate HTML quality report."""
    healthy = sum(1 for r in results if r['status'] == 'healthy')
    degraded = sum(1 for r in results if r['status'] == 'degraded')
    critical = sum(1 for r in results if r['status'] == 'critical')
    errors = sum(1 for r in results if r['status'] == 'error')
    
    report = f"""
    <h2>Model Quality Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>
    
    <h3>Summary</h3>
    <ul>
        <li>✅ Healthy: {healthy} zones</li>
        <li>⚠️ Degraded: {degraded} zones</li>
        <li>🚨 Critical: {critical} zones</li>
        <li>❌ Errors: {errors} zones</li>
    </ul>
    
    <h3>Zone Details</h3>
    <table border="1">
        <tr><th>Zone</th><th>Status</th><th>MAPE</th><th>R²</th><th>Issues</th></tr>
    """
    
    for result in results:
        status_emoji = {
            'healthy': '✅',
            'degraded': '⚠️',
            'critical': '🚨',
            'error': '❌',
            'missing': '❓'
        }.get(result['status'], '❓')
        
        mape = result.get('mape', 'N/A')
        r2 = result.get('r2', 'N/A')
        issues = '; '.join(result.get('issues', []))
        
        report += f"""
        <tr>
            <td>{result['zone']}</td>
            <td>{status_emoji} {result['status']}</td>
            <td>{mape if mape == 'N/A' else f'{mape:.2f}%'}</td>
            <td>{r2 if r2 == 'N/A' else f'{r2:.4f}'}</td>
            <td>{issues}</td>
        </tr>
        """
    
    report += "</table>"
    return report


def send_alert_if_needed(results: List[Dict]):
    """Send email alert if any zones have issues."""
    issues = [r for r in results if r['status'] != 'healthy']
    
    if not issues:
        logger.info("All zones healthy, no alert needed")
        return
    
    critical_issues = [r for r in issues if r['status'] in ['critical', 'error']]
    
    subject = f"Model Quality Alert - {len(issues)} zones need attention"
    if critical_issues:
        subject = f"🚨 CRITICAL: Model Quality Alert - {len(critical_issues)} zones critical"
    
    report = generate_quality_report(results)
    
    # Log the alert (in production, replace with actual email sending)
    logger.warning(f"ALERT: {subject}")
    logger.warning(f"Issues found in zones: {[r['zone'] for r in issues]}")
    
    # Save report to file
    report_file = Path(f"logs/quality_report_{datetime.now().strftime('%Y%m%d_%H%M')}.html")
    with open(report_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Quality report saved to {report_file}")


def main():
    """Main monitoring function."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/quality_monitor.log'),
            logging.StreamHandler()
        ]
    )
    
    logger.info("Starting model quality monitoring")
    
    # Monitor all zones
    results = monitor_all_zones()
    
    # Save results
    results_file = Path(f"logs/quality_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Send alerts if needed
    send_alert_if_needed(results)
    
    logger.info("Quality monitoring completed")


if __name__ == "__main__":
    main()