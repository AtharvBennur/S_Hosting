import hashlib

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.integrity import hash_file, verify_file


def test_sha256_generation_matches_standard_library(tmp_path):
    path = tmp_path / 'dataset.csv'
    content = b'project_id,project_name\n1,Drain repair\n'
    path.write_bytes(content)

    assert hash_file(path) == hashlib.sha256(content).hexdigest()


def test_same_file_has_same_hash(tmp_path):
    path = tmp_path / 'dataset.csv'
    path.write_bytes(b'same bytes')

    assert hash_file(path) == hash_file(path)


def test_modified_file_has_different_hash(tmp_path):
    path = tmp_path / 'dataset.csv'
    path.write_bytes(b'original bytes')
    original_hash = hash_file(path)

    path.write_bytes(b'modified bytes')

    assert hash_file(path) != original_hash


def test_integrity_verification_succeeds(tmp_path):
    path = tmp_path / 'dataset.csv'
    path.write_bytes(b'unchanged bytes')
    stored_hash = hash_file(path)

    assert verify_file(path, stored_hash)


def test_integrity_verification_fails_after_modification(tmp_path):
    path = tmp_path / 'dataset.csv'
    path.write_bytes(b'original bytes')
    stored_hash = hash_file(path)
    path.write_bytes(b'tampered bytes')

    assert not verify_file(path, stored_hash)


def test_missing_file_is_reported_by_hashing_utility(tmp_path):
    with pytest.raises(FileNotFoundError):
        hash_file(tmp_path / 'missing.csv')


def test_integrity_endpoint_requires_authentication():
    client = TestClient(app)

    response = client.get('/api/datasets/1/integrity')

    assert response.status_code == 401
