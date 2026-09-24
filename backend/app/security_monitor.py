"""Centralized security-event and incident-alert helpers."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.database.models import SecurityAlertModel


SEVERITIES = {'INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}
STATUSES = {'OPEN', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE'}
MANAGED_STATUSES = {'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE'}
MONITORED_AUDIT_EVENTS = {
    'AUTH_LOGIN_FAILED': ('AUTHENTICATION', 'Failed authentication attempt', 'A failed authentication attempt was recorded.'),
    'AUTH_RATE_LIMITED': ('RATE_LIMIT', 'Authentication rate limit reached', 'Authentication attempts exceeded the configured threshold.'),
    'API_RATE_LIMITED': ('RATE_LIMIT', 'API rate limit reached', 'An authenticated client exceeded an API rate limit.'),
    'AUTH_SCOPE_MISMATCH': ('AUTHORIZATION', 'Jurisdiction mismatch', 'A request did not match the account jurisdiction.'),
    'DATASET_UPLOAD_REJECTED_TYPE': ('UPLOAD', 'Upload type rejected', 'An uploaded file was rejected by upload security controls.'),
    'DATASET_UPLOAD_REJECTED_CONTENT': ('UPLOAD', 'Upload content rejected', 'An uploaded file was rejected by content validation.'),
    'DATASET_UPLOAD_REJECTED_PATH': ('UPLOAD', 'Upload path rejected', 'An uploaded filename or path was rejected.'),
    'DATASET_UPLOAD_REJECTED_SIZE': ('UPLOAD', 'Upload size rejected', 'An uploaded file exceeded the configured size limit.'),
    'DATASET_UPLOAD_REJECTED_SCHEMA': ('UPLOAD', 'Upload schema rejected', 'An uploaded dataset did not satisfy the required schema.'),
    'SECURITY_SCAN_BLOCKED': ('MALWARE_SCAN', 'Security scan blocked upload', 'An uploaded file was blocked by security scanning.'),
    'SECURITY_SCAN_SUSPICIOUS': ('MALWARE_SCAN', 'Security scan flagged upload', 'An uploaded file was flagged for security review.'),
    'DATASET_UPLOAD_HASH_FAILED': ('INTEGRITY', 'Dataset hash failed', 'A dataset integrity hash could not be calculated.'),
    'PII_REVIEW_REQUIRED': ('PRIVACY', 'Privacy review required', 'A dataset requires privacy review.'),
}


def monitored_event(action: str) -> tuple[str, str, str] | None:
    return MONITORED_AUDIT_EVENTS.get(action)


def classify_severity(event_type: str, category: str, requested: str | None = None) -> str:
    if requested in SEVERITIES:
        return requested
    if event_type in {'AUDIT_INTEGRITY_FAILED', 'DATASET_INTEGRITY_FAILED', 'SECRET_DETECTED', 'DATASET_SECURITY_SCAN_BLOCKED'}:
        return 'HIGH'
    if event_type in {'AUTH_LOGIN_RATE_LIMITED', 'API_RATE_LIMITED', 'PII_REVIEW_REQUIRED', 'AUTH_FORBIDDEN_ACCESS'}:
        return 'MEDIUM'
    if category in {'MALWARE_SCAN', 'INTEGRITY', 'AUDIT_INTEGRITY', 'SECRET_DETECTION'}:
        return 'HIGH'
    return 'LOW' if 'FAILED' in event_type else 'INFO'


def _safe_text(value: Any, fallback: str) -> str:
    text = str(value or '').strip()
    return text[:500] if text else fallback


def record_security_event(
    db: Session,
    *,
    event_type: str,
    category: str,
    title: str,
    description: str,
    severity: str | None = None,
    actor_user_id: int | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    scope_state: str | None = None,
    scope_id: str | None = None,
    dedup_window_seconds: int = 300,
) -> tuple[SecurityAlertModel, bool]:
    """Create or correlate a security alert; return (alert, created)."""
    if severity not in (None, *SEVERITIES):
        raise ValueError('Invalid security alert severity.')
    now = datetime.utcnow()
    resolved_cutoff = now - timedelta(seconds=max(0, dedup_window_seconds))
    query = db.query(SecurityAlertModel).filter(
        SecurityAlertModel.event_type == event_type,
        SecurityAlertModel.category == category,
        SecurityAlertModel.target_type == target_type,
        SecurityAlertModel.target_id == target_id,
        SecurityAlertModel.scope_state == scope_state,
        SecurityAlertModel.scope_id == scope_id,
        SecurityAlertModel.status.in_(['OPEN', 'ACKNOWLEDGED', 'INVESTIGATING']),
        SecurityAlertModel.last_seen_at >= resolved_cutoff,
    )
    existing = query.order_by(SecurityAlertModel.id.desc()).first()
    if existing:
        existing.last_seen_at = now
        existing.occurrence_count += 1
        return existing, False
    alert = SecurityAlertModel(
        event_type=_safe_text(event_type, 'SECURITY_EVENT'), category=_safe_text(category, 'SYSTEM'),
        severity=classify_severity(event_type, category, severity), status='OPEN',
        title=_safe_text(title, 'Security event detected'), safe_description=_safe_text(description, 'Security event requires review.'),
        source='application', actor_user_id=actor_user_id, target_type=_safe_text(target_type, '') or None,
        target_id=_safe_text(target_id, '') or None, scope_state=_safe_text(scope_state, '') or None,
        scope_id=_safe_text(scope_id, '') or None, first_seen_at=now, last_seen_at=now,
        occurrence_count=1, created_at=now, updated_at=now,
    )
    db.add(alert)
    db.flush()
    return alert, True


def security_alert_payload(alert: SecurityAlertModel) -> dict[str, Any]:
    return {
        'id': alert.id, 'event_type': alert.event_type, 'category': alert.category,
        'severity': alert.severity, 'status': alert.status, 'title': alert.title,
        'safe_description': alert.safe_description, 'source': alert.source,
        'target_type': alert.target_type, 'target_id': alert.target_id,
        'occurrence_count': alert.occurrence_count,
        'assigned_to_user_id': alert.assigned_to_user_id,
        'resolution_note': alert.resolution_note,
        'first_seen_at': alert.first_seen_at.isoformat() if alert.first_seen_at else None,
        'last_seen_at': alert.last_seen_at.isoformat() if alert.last_seen_at else None,
        'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
    }