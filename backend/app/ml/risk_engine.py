from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


RISK_CONFIG = {
    'ml_anomaly_weight': 0.40,
    'utilization_weight': 0.20,
    'delay_weight': 0.15,
    'cost_overrun_weight': 0.10,
    'peer_deviation_weight': 0.10,
    'duplicate_weight': 0.03,
    'data_quality_weight': 0.02,
}


def classify_risk(score: float) -> str:
    if score >= 80:
        return 'CRITICAL'
    if score >= 60:
        return 'HIGH'
    if score >= 35:
        return 'MEDIUM'
    return 'LOW'


def calculate_risk(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result['ml_score_component'] = result.get('normalized_ml_score', pd.Series(0.5, index=result.index)).fillna(0.5)
    result['utilization_ratio'] = pd.to_numeric(result.get('utilization_ratio', pd.Series(np.nan, index=result.index)), errors='coerce')
    result['delay_days'] = pd.to_numeric(result.get('delay_days', pd.Series(np.nan, index=result.index)), errors='coerce')
    result['cost_overrun_flag'] = (
        result.get('expenditure', pd.Series(np.nan, index=result.index)).fillna(0)
        > result.get('sanction_amount', pd.Series(np.nan, index=result.index)).fillna(0)
    )
    result['duplicate_flag'] = result.get('duplicate_flag', pd.Series(False, index=result.index)).fillna(False)
    result['data_quality_flag'] = result.get('data_quality_flag', pd.Series(False, index=result.index)).fillna(False)

    utilization_score = pd.Series(0.0, index=result.index)
    if 'utilization_ratio' in result.columns:
        utilization_score = pd.to_numeric(result['utilization_ratio'], errors='coerce').fillna(0).clip(lower=0, upper=1.5)
        utilization_score = (utilization_score / 1.5).clip(lower=0, upper=1)
    delay_score = pd.Series(0.0, index=result.index)
    if 'delay_days' in result.columns:
        delay_score = pd.to_numeric(result['delay_days'], errors='coerce').fillna(0).clip(lower=0)
        delay_score = (delay_score / 365).clip(lower=0, upper=1)

    sanction_amount = pd.to_numeric(result.get('sanction_amount', pd.Series(np.nan, index=result.index)), errors='coerce').fillna(0)
    expenditure_amount = pd.to_numeric(result.get('expenditure', pd.Series(np.nan, index=result.index)), errors='coerce').fillna(0)
    overrun_ratio = (expenditure_amount / sanction_amount.replace(0, np.nan)).fillna(0)
    cost_overrun_score = ((overrun_ratio.sub(1).clip(lower=0) / 0.5).clip(lower=0, upper=1)).fillna(0)

    peer_deviation = pd.to_numeric(result.get('contextual_cost_deviation', pd.Series(np.nan, index=result.index)), errors='coerce')
    peer_deviation_score = ((peer_deviation.sub(1).abs() / 1.5).clip(lower=0, upper=1)).fillna(0)
    duplicate_score = result['duplicate_flag'].astype(float)
    data_quality_score = result['data_quality_flag'].astype(float)

    result['ml_score_component'] = result['ml_score_component'].clip(0, 1)
    result['utilization_score_component'] = utilization_score
    result['delay_score_component'] = delay_score
    result['cost_overrun_score_component'] = cost_overrun_score
    result['peer_deviation_score_component'] = peer_deviation_score
    result['duplicate_score_component'] = duplicate_score
    result['data_quality_score_component'] = data_quality_score

    risk_score = (
        RISK_CONFIG['ml_anomaly_weight'] * result['ml_score_component']
        + RISK_CONFIG['utilization_weight'] * utilization_score
        + RISK_CONFIG['delay_weight'] * delay_score
        + RISK_CONFIG['cost_overrun_weight'] * cost_overrun_score
        + RISK_CONFIG['peer_deviation_weight'] * peer_deviation_score
        + RISK_CONFIG['duplicate_weight'] * duplicate_score
        + RISK_CONFIG['data_quality_weight'] * data_quality_score
    ) * 100
    result['risk_score'] = risk_score.clip(lower=0, upper=100)
    result['risk_level'] = result.apply(
        lambda row: 'DATA_QUALITY_REVIEW' if bool(row.get('data_quality_flag', False)) else classify_risk(row['risk_score']),
        axis=1,
    )
    result['reasons'] = result.apply(lambda row: [
        'AI detected an unusual project pattern' if row['ml_score_component'] > 0.7 else 'Project pattern is within the monitored baseline',
        'Utilization is unusually high' if pd.notna(row.get('utilization_ratio')) and row['utilization_ratio'] > 1.1 else 'Utilization is within expected range',
        'Project is delayed beyond expected completion' if pd.notna(row.get('delay_days')) and row['delay_days'] > 30 else 'No delay risk observed',
        'Cost overrun detected' if row.get('cost_overrun_flag') else 'No cost overrun indicator',
        'Possible duplicate project pattern' if row.get('duplicate_flag') else 'No duplicate indicators detected',
        'Data quality issue requires review' if row.get('data_quality_flag') else 'Data quality is acceptable',
    ], axis=1)
    return result
