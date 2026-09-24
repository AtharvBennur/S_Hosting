from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings
from app.ml.feature_engineering import engineer_features
from app.ml.inference import infer_from_dataframe
from app.ml.integration import integrate_files
from app.ml.pipeline import train_pipeline
from app.ml.risk_engine import calculate_risk


def describe_numeric(series: pd.Series) -> str:
    if series.empty:
        return 'n/a'
    q = series.quantile([0, 0.5, 0.75, 0.9, 0.95, 0.98, 0.99, 1])
    return (
        f"min={series.min():.6f} max={series.max():.6f} median={q[0.5]:.6f} "
        f"p75={q[0.75]:.6f} p90={q[0.9]:.6f} p95={q[0.95]:.6f} p98={q[0.98]:.6f} p99={q[0.99]:.6f}"
    )


def describe_scores(series: pd.Series) -> str:
    if series.empty:
        return 'n/a'
    q = series.quantile([0, 0.5, 0.75, 0.9, 0.95, 0.98, 0.99, 1])
    return (
        f"min={series.min():.6f} max={series.max():.6f} median={q[0.5]:.6f} "
        f"p95={q[0.95]:.6f} p99={q[0.99]:.6f}"
    )


def print_section(title: str):
    print(f"\n=== {title} ===")


if __name__ == '__main__':
    print('Loading configured real MPLADS demo workbooks from backend/demo_data...')
    paths = [Path(settings.demo_data_dir) / name for name in settings.default_demo_files]

    unified, summary = integrate_files(paths)

    print_section('ROWS')
    print(f"integration rows: {len(unified)}")
    print(f"unique canonical project IDs: {unified['project_id'].nunique()}")
    print(f"duplicate canonical IDs: {int(unified['project_id'].duplicated().sum())}")

    print_section('FEATURES: integrated data')
    for column in ['sanction_amount', 'expenditure', 'utilization_ratio', 'elapsed_days_as_of', 'contextual_cost_deviation']:
        if column not in unified.columns:
            print(f"{column}: missing from integrated data")
            continue
        if column in {'utilization_ratio', 'contextual_cost_deviation'}:
            print(f"{column}: {describe_numeric(pd.to_numeric(unified[column], errors='coerce'))}")
        else:
            print(f"{column}: {describe_numeric(pd.to_numeric(unified[column], errors='coerce'))}")

    print_section('FEATURE ENGINEERING')
    engineered = engineer_features(unified)
    for column in ['sanction_amount', 'expenditure', 'utilization_ratio', 'delay_days', 'elapsed_days_as_of', 'contextual_cost_deviation']:
        if column not in engineered.columns:
            print(f"{column}: missing from engineered data")
            continue
        print(f"{column}: {describe_numeric(pd.to_numeric(engineered[column], errors='coerce'))}")

    print_section('ML MODEL / INFERENCE')
    try:
        inferred = infer_from_dataframe(engineered)
    except FileNotFoundError:
        print('No trained model artifact found. Training on configured real demo data now...')
        train_pipeline(unified)
        inferred = infer_from_dataframe(engineered)

    print(f"ML anomaly score stats: {describe_scores(pd.to_numeric(inferred['ml_anomaly_score'], errors='coerce'))}")
    print(f"number of ML anomalies: {int(inferred['ml_anomaly_flag'].sum())}")
    print(f"normalized ML p95/p99: {inferred['normalized_ml_score'].quantile([0.95,0.99]).to_dict()}")

    print_section('RISK')
    results = calculate_risk(inferred)
    print(f"risk score stats: {describe_scores(pd.to_numeric(results['risk_score'], errors='coerce'))}")
    print(f"risk counts: {results['risk_level'].value_counts().to_dict()}")

    print_section('DATA QUALITY')
    print(f"number of data-quality records: {int(results.get('data_quality_flag', pd.Series(False, index=results.index)).fillna(False).sum())}")
    print(f"number of missing sanction values: {int(results['sanction_amount'].isna().sum())}")
    print(f"number of missing expenditure values: {int(results['expenditure'].isna().sum())}")
    print(f"number of invalid dates: {int(results[['expected_completion_date', 'actual_completion_date', 'sanction_date']].isna().any(axis=1).sum())}")
    print(f"number of invalid IDs: {int(results['project_id'].fillna('').astype(str).str.strip().eq('').sum())}")
    print(f"number of missing model inputs: {int(results['missing_model_inputs'].fillna(False).sum())}")

    print_section('REFERENCE TARGETS')
    print('Verified notebook target (for comparison only):')
    print('22,000 total projects')
    print('LOW=17672, MEDIUM=3020, HIGH=159, CRITICAL=1, DATA_QUALITY_REVIEW=1148')
