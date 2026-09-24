import pandas as pd

from app.ml.feature_engineering import engineer_features
from app.ml.pipeline import train_pipeline


def test_training_pipeline_runs_on_sample_data(isolated_model_path):
    df = pd.DataFrame([
        {
            'project_name': 'Road Repair Work',
            'state': 'Odisha',
            'district': 'Cuttack',
            'sanction_amount': 500000,
            'expenditure': 300000,
            'project_category': 'Roads',
        },
        {
            'project_name': 'Drainage Improvement',
            'state': 'Odisha',
            'district': 'Cuttack',
            'sanction_amount': 750000,
            'expenditure': 420000,
            'project_category': 'Drainage',
        },
        {
            'project_name': 'Critical Water Supply',
            'state': 'Odisha',
            'district': 'Puri',
            'sanction_amount': 2500000,
            'expenditure': 2200000,
            'project_category': 'Water',
        },
        {
            'project_name': 'School Infrastructure',
            'state': 'Odisha',
            'district': 'Puri',
            'sanction_amount': 1800000,
            'expenditure': 900000,
            'project_category': 'Education',
        },
    ])

    result = train_pipeline(df)
    assert result['status'] == 'trained'
    assert 'features' in result
    assert len(result['features']) >= 4
    assert isolated_model_path.exists()


def test_ongoing_work_overdue_at_as_of_date_gets_delay_signal():
    frame = pd.DataFrame([{
        'project_name': 'Community hall', 'state': 'Bihar', 'district': 'Patna',
        'sanction_amount': 100000, 'expenditure': 20000,
        'expected_completion_date': '2026-01-15', 'actual_completion_date': None,
    }])

    result = engineer_features(frame, as_of_date='2026-02-01')

    assert result.loc[0, 'delay_days'] == 17
