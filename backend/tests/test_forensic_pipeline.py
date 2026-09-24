import pandas as pd
import pytest
from pathlib import Path

from app.ml.inference import infer_from_dataframe, load_model, prepare_model_features
from app.ml.pipeline import run_inference_pipeline, train_pipeline


SAMPLE_DATA = Path(__file__).resolve().parents[1] / 'uploads' / 'mplads_demo_180.csv'


def test_saved_model_inference_separates_real_records(isolated_model_path):
    frame = pd.read_csv(SAMPLE_DATA)
    train_pipeline(frame)
    result = run_inference_pipeline(frame)
    artifact = load_model()
    features = prepare_model_features(result).fillna(pd.Series(artifact['metadata']['medians'])).fillna(0)

    assert list(features.columns) == artifact['metadata']['feature_columns']
    assert features.notna().all().all()
    assert result['ml_anomaly_score'].nunique() > 10
    assert result['normalized_ml_score'].between(0, 1).all()
    assert result['risk_level'].isin(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'DATA_QUALITY_REVIEW']).all()
    assert result.loc[result['risk_level'] == 'DATA_QUALITY_REVIEW', 'data_quality_flag'].all()
    assert result['risk_level'].isin(['HIGH', 'CRITICAL']).any()


def test_risk_changes_when_financial_signal_changes(isolated_model_path):
    frame = pd.read_csv(SAMPLE_DATA).head(30).copy()
    train_pipeline(frame)
    baseline = run_inference_pipeline(frame)
    changed = frame.copy()
    changed.loc[0, 'expenditure'] = changed.loc[0, 'sanction_amount'] * 1.5
    changed_result = run_inference_pipeline(changed)

    assert changed_result.loc[0, 'risk_score'] > baseline.loc[0, 'risk_score']


def test_data_quality_rows_are_flagged_for_review(isolated_model_path):
    frame = pd.read_csv(SAMPLE_DATA).head(5).copy()
    frame['data_quality_flag'] = [True, False, True, False, False]
    frame['duplicate_flag'] = False
    train_pipeline(frame)

    result = run_inference_pipeline(frame)

    assert result.loc[0, 'risk_level'] == 'DATA_QUALITY_REVIEW'
    assert result.loc[1, 'risk_level'] in {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}


def test_stable_baseline_score_does_not_depend_on_batch_companions(isolated_model_path):
    frame = pd.read_csv(SAMPLE_DATA).head(40).copy()
    train_pipeline(frame)
    target = pd.DataFrame([{
        'sanction_amount': 100000, 'utilization_ratio': 0.4,
        'contextual_cost_deviation': 1.2, 'elapsed_days_as_of': 180,
    }])
    with_companions = pd.concat([target, pd.DataFrame([{
        'sanction_amount': 900000, 'utilization_ratio': 1.1,
        'contextual_cost_deviation': 2.0, 'elapsed_days_as_of': 500,
    }])], ignore_index=True)

    isolated = infer_from_dataframe(target)
    batched = infer_from_dataframe(with_companions)

    assert isolated.loc[isolated.index[0], 'normalized_ml_score'] == batched.loc[0, 'normalized_ml_score']


def test_missing_model_artifact_has_clear_error(isolated_model_path):
    with pytest.raises(FileNotFoundError, match='Model artifact not found'):
        load_model()


def test_model_metadata_has_a_version(isolated_model_path):
    train_pipeline(pd.read_csv(SAMPLE_DATA).head(20))
    metadata = load_model()['metadata']
    assert metadata['model_version'].startswith('iforest-')
    assert metadata['training_rows'] == 20
