from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd


EMAIL_RE = re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.IGNORECASE)
PHONE_RE = re.compile(r'(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)')
AADHAAR_RE = re.compile(r'(?<!\d)(?:\d{4}[ -]?){2}\d{4}(?!\d)')
PAN_RE = re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b', re.IGNORECASE)
ACCOUNT_RE = re.compile(r'(?<!\d)\d{9,18}(?!\d)')
GPS_RE = re.compile(r'(?<!\d)-?\d{1,3}\.\d{4,}(?!\d)')

HEADER_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ('SECRET', ('password', 'passwd', 'secret', 'api_key', 'apikey', 'api_token', 'access_token', 'auth_token', 'jwt'), 'HIGH'),
    ('AADHAAR', ('aadhaar', 'aadhar', 'uidai'), 'HIGH'),
    ('PAN', ('pan_number', 'pan_no', 'permanent_account_number'), 'HIGH'),
    ('BANK_ACCOUNT', ('bank_account', 'account_number', 'account_no', 'bank_ac'), 'HIGH'),
    ('CARD', ('credit_card', 'debit_card', 'card_number', 'cvv'), 'HIGH'),
    ('EMAIL', ('email', 'e_mail', 'email_address'), 'HIGH'),
    ('PHONE', ('phone', 'mobile', 'telephone', 'contact_number'), 'HIGH'),
    ('ADDRESS', ('address', 'residential_address', 'postal_address', 'home_address'), 'HIGH'),
    ('DATE_OF_BIRTH', ('dob', 'date_of_birth', 'birth_date'), 'HIGH'),
    ('GPS', ('latitude', 'longitude', 'gps', 'coordinates'), 'MEDIUM'),
)

PUBLIC_CONTEXT_COLUMNS = {
    'project_name', 'project_id', 'project_code', 'project_category', 'category',
    'state', 'district', 'constituency', 'agency', 'vendor_name', 'status',
    'sanction_amount', 'expenditure', 'allocation_limit', 'mp_name',
}


@dataclass(frozen=True)
class PIIClassification:
    pii_type: str
    confidence: str
    reason: str
    secret: bool = False


def normalize_header(value: object) -> str:
    return re.sub(r'[^a-z0-9]+', '_', str(value).strip().casefold()).strip('_')


def classify_column(column: object) -> PIIClassification | None:
    normalized = normalize_header(column)
    if normalized in PUBLIC_CONTEXT_COLUMNS:
        return None
    for pii_type, names, confidence in HEADER_RULES:
        if normalized in names or any(name in normalized for name in names):
            return PIIClassification(pii_type, confidence, 'suspicious column name', pii_type == 'SECRET')
    return None


def _value_matches(value: object, column: object) -> PIIClassification | None:
    text = str(value).strip()
    if not text or text.casefold() in {'nan', 'none', 'nat'}:
        return None
    header = normalize_header(column)
    if EMAIL_RE.search(text):
        return PIIClassification('EMAIL', 'HIGH', 'email-like value')
    if PAN_RE.search(text):
        return PIIClassification('PAN', 'HIGH', 'PAN-like value; not validity proof')
    if AADHAAR_RE.search(text) and len(re.sub(r'\D', '', text)) == 12:
        return PIIClassification('AADHAAR', 'HIGH', 'Aadhaar-like value; not validity proof')
    if PHONE_RE.search(text) and ('phone' in header or 'mobile' in header or 'telephone' in header or 'contact' in header):
        return PIIClassification('PHONE', 'HIGH', 'phone-like value in contact column')
    if ('latitude' in header or 'longitude' in header or 'gps' in header) and GPS_RE.search(text):
        return PIIClassification('GPS', 'MEDIUM', 'coordinate-like value')
    if ('account' in header or 'bank' in header) and ACCOUNT_RE.fullmatch(re.sub(r'[^0-9]', '', text)):
        return PIIClassification('BANK_ACCOUNT', 'MEDIUM', 'account-number-like value; not validity proof')
    if 'address' in header and len(text) >= 8:
        return PIIClassification('ADDRESS', 'HIGH', 'address-like column value')
    return None


def scan_dataframe(df: pd.DataFrame, sample_size: int = 1000) -> dict[str, Any]:
    sampled = len(df) > sample_size
    frame = df.head(sample_size) if sampled else df
    findings: dict[tuple[str, str], dict[str, Any]] = {}
    for column in frame.columns:
        header_classification = classify_column(column)
        values = frame[column].dropna()
        classification = header_classification
        count = 0
        if classification:
            count = int(values.astype(str).str.strip().ne('').sum())
        else:
            for value in values:
                value_classification = _value_matches(value, column)
                if value_classification:
                    classification = value_classification
                    count += 1
            if classification and count == 0:
                continue
        if classification:
            key = (str(column), classification.pii_type)
            findings[key] = {
                'column': str(column),
                'type': classification.pii_type,
                'confidence': classification.confidence,
                'count': count,
                'reason': classification.reason,
                'secret': classification.secret,
            }
    items = list(findings.values())
    secrets_detected = any(item['secret'] for item in items)
    return {
        'privacy_status': 'BLOCKED' if secrets_detected else 'REVIEW_REQUIRED' if items else 'NO_PII_DETECTED_IN_SCANNED_DATA',
        'pii_detected': bool(items),
        'sampled': sampled,
        'scanned_rows': len(frame),
        'total_rows': len(df),
        'columns': [{key: item[key] for key in ('column', 'type', 'confidence', 'count')} for item in items],
    }


def mask_value(value: object, pii_type: str) -> str:
    text = str(value)
    if pii_type == 'EMAIL' and '@' in text:
        local, domain = text.split('@', 1)
        return f'{local[:1]}*****{local[-1:] if len(local) > 1 else ""}@{domain}'
    if pii_type == 'ADDRESS':
        return '[REDACTED]'
    if pii_type == 'PHONE':
        digits = re.sub(r'\D', '', text)
        return '*' * max(0, len(digits) - 4) + digits[-4:]
    if pii_type == 'AADHAAR':
        digits = re.sub(r'\D', '', text)
        return '*' * max(0, len(digits) - 4) + digits[-4:]
    if pii_type == 'PAN':
        return '*' * max(0, len(text) - 5) + text[-5:]
    if pii_type in {'BANK_ACCOUNT', 'CARD'}:
        digits = re.sub(r'\D', '', text)
        return '*' * max(0, len(digits) - 4) + digits[-4:]
    if pii_type in {'SECRET', 'GPS', 'DATE_OF_BIRTH'}:
        return '[REDACTED]'
    return '[REDACTED]'
