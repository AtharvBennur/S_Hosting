from __future__ import annotations

import json
from datetime import datetime, timezone
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from app.config import settings
from app.ml.feature_engineering import engineer_features
from app.ml.inference import MINIMUM_APPROVED_TRAINING_ROWS, infer_from_dataframe, prepare_model_features, save_model
from app.ml.peer_benchmarking import compute_peer_context
from app.ml.preprocessing import coerce_numeric, normalize_dataframe_columns, validate_dataset
from app.ml.risk_engine import calculate_risk


TRAINING_MODEL_PATH = Path(settings.model_dir) / 'mplads_isolation_forest.joblib'


def train_pipeline(df: pd.DataFrame, *, source_files: list[str] | None = None, enforce_minimum: bool = False) -> dict:
    normalized = normalize_dataframe_columns(df)
    required = ['project_name', 'state', 'district', 'sanction_amount', 'expenditure']
    for col in required:
        if col not in normalized.columns:
            raise ValueError(f'Missing required field for training: {col}')
    normalized['sanction_amount'] = coerce_numeric(normalized['sanction_amount'])
    normalized['expenditure'] = coerce_numeric(normalized['expenditure'])
    normalized['utilization_ratio'] = normalized['expenditure'] / normalized['sanction_amount'].replace(0, pd.NA)
    normalized['project_category'] = normalized.get('project_category', normalized['project_name'])
    normalized['state'] = normalized.get('state', 'Unknown')
    normalized['district'] = normalized.get('district', 'Unknown')
    normalized = engineer_features(normalized)
    feature_matrix = prepare_model_features(normalized)
    feature_matrix['contextual_cost_deviation'] = normalized['contextual_cost_deviation'].fillna(1)
    feature_matrix['log_contextual_cost_deviation'] = np.log1p(feature_matrix['contextual_cost_deviation'].clip(lower=0.0001))
    feature_matrix = feature_matrix[['log_sanction_amount', 'utilization_ratio', 'log_contextual_cost_deviation', 'elapsed_days_as_of']]
    model_features = feature_matrix.fillna(0)
    if enforce_minimum and len(model_features) < MINIMUM_APPROVED_TRAINING_ROWS:
        raise ValueError(f'Approved baseline training requires at least {MINIMUM_APPROVED_TRAINING_ROWS} rows')
    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(model_features)
    baseline_scores = -model.decision_function(model_features)
    fingerprint = hashlib.sha256(
        pd.util.hash_pandas_object(model_features, index=True).values.tobytes()
    ).hexdigest()[:12]
    metadata = {
        'feature_columns': list(feature_matrix.columns),
        'medians': model_features.median().to_dict(),
        'contamination': 0.05,
        'random_state': 42,
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'training_rows': int(len(model_features)),
        'source_files': source_files or [],
        'model_version': f'iforest-{fingerprint}',
        # Robust fixed calibration makes later scores comparable across runs.
        'score_calibration': {
            'low': float(np.quantile(baseline_scores, 0.05)),
            'high': float(np.quantile(baseline_scores, 0.95)),
        },
    }
    save_model(model, metadata)
    return {
        'status': 'trained', 'features': list(feature_matrix.columns),
        'artifact': str(TRAINING_MODEL_PATH), 'model_version': metadata['model_version'],
        'training_rows': metadata['training_rows'],
    }


def run_inference_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    validated = normalize_dataframe_columns(df)
    valid, missing, suggestions = validate_dataset(validated)
    if not valid:
        raise ValueError(f"Dataset incompatible. Missing required fields: {missing}")
    validated = validated.copy()
    validated['sanction_amount'] = coerce_numeric(validated.get('sanction_amount', pd.Series([0] * len(validated))))
    validated['expenditure'] = coerce_numeric(validated.get('expenditure', pd.Series([0] * len(validated))))
    if 'project_name' not in validated.columns:
        validated['project_name'] = 'Unnamed Project'
    if 'district' not in validated.columns:
        validated['district'] = 'Unknown'
    if 'state' not in validated.columns:
        validated['state'] = 'Unknown'
    validated = engineer_features(validated)
    if 'contextual_cost_deviation' not in validated.columns:
        validated['contextual_cost_deviation'] = 1
    validated['utilization_ratio'] = np.where(validated['sanction_amount'].gt(0), validated['expenditure'] / validated['sanction_amount'], np.nan)
    validated['data_quality_flag'] = (
        validated.get('data_quality_flag', pd.Series(False, index=validated.index)).fillna(False)
        | validated['missing_model_inputs']
    )
    inferred = infer_from_dataframe(validated)
    return calculate_risk(inferred)
