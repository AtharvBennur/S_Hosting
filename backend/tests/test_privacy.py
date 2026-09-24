import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.privacy import mask_value, scan_dataframe


def test_privacy_scan_detects_sensitive_values_without_returning_raw_data():
    frame = pd.DataFrame({
        'contact_email': ['test@example.com'],
        'mobile_number': ['9876543210'],
        'aadhaar_number': ['123412341234'],
        'pan_number': ['ABCDE1234F'],
        'project_name': ['Construction of Government School'],
        'district': ['Dharwad'],
        'state': ['Karnataka'],
        'amount': [500000],
    })

    result = scan_dataframe(frame)
    serialized = str(result)

    assert result['privacy_status'] == 'REVIEW_REQUIRED'
    assert result['pii_detected'] is True
    assert {item['type'] for item in result['columns']} >= {'EMAIL', 'PHONE', 'AADHAAR', 'PAN'}
    assert 'test@example.com' not in serialized
    assert '9876543210' not in serialized
    assert '123412341234' not in serialized
    assert 'ABCDE1234F' not in serialized


def test_secret_columns_are_blocked_without_storing_secret_values():
    result = scan_dataframe(pd.DataFrame({'api_token': ['super-secret-token']}))

    assert result['privacy_status'] == 'BLOCKED'
    assert result['columns'][0]['type'] == 'SECRET'
    assert 'super-secret-token' not in str(result)


def test_public_mplads_fields_are_not_automatically_pii():
    result = scan_dataframe(pd.DataFrame({
        'project_name': ['Construction of Government School'],
        'district': ['Dharwad'],
        'state': ['Karnataka'],
        'constituency': ['Dharwad'],
        'mp_name': ['Public Representative'],
        'sanction_amount': [500000],
        'expenditure': [200000],
    }))

    assert result['privacy_status'] == 'NO_PII_DETECTED_IN_SCANNED_DATA'
    assert result['columns'] == []


def test_large_scan_reports_sampling():
    result = scan_dataframe(pd.DataFrame({'project_name': ['Road'] * 5, 'email': ['test@example.com'] * 5}), sample_size=2)

    assert result['sampled'] is True
    assert result['scanned_rows'] == 2
    assert result['total_rows'] == 5


def test_masking_never_returns_complete_sensitive_values():
    assert mask_value('test@example.com', 'EMAIL') == 't*****t@example.com'
    assert mask_value('9876543210', 'PHONE') == '******3210'
    assert mask_value('123412341234', 'AADHAAR') == '********1234'
    assert mask_value('ABCDE1234F', 'PAN') == '*****1234F'
    assert mask_value('12 Private Road, Dharwad', 'ADDRESS') == '[REDACTED]'


def test_privacy_endpoint_requires_authentication():
    response = TestClient(app).post('/api/datasets/1/privacy-scan')

    assert response.status_code == 401
