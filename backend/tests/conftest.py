from pathlib import Path

import pytest


@pytest.fixture
def isolated_model_path(monkeypatch, tmp_path: Path):
    """Keep tests that train a model away from the approved production artifact."""
    from app.ml import inference
    path = tmp_path / 'models' / 'mplads_isolation_forest.joblib'
    monkeypatch.setattr(inference, 'MODEL_PATH', path)
    return path
