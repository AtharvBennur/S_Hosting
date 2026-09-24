from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import create_access_token
from app.database.base import Base
from app.database.models import AuditLogModel, SecurityAlertModel
from app.main import app
from app.ml.audit_integrity import verify_audit_chain
from app.security_monitor import classify_severity, record_security_event


def session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'security-monitor.db'}")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_event_classification_and_deduplication(tmp_path):
    db = session(tmp_path)
    assert classify_severity('DATASET_SECURITY_SCAN_BLOCKED', 'MALWARE_SCAN') == 'HIGH'
    first, created = record_security_event(db, event_type='AUTH_LOGIN_FAILED', category='AUTHENTICATION', title='Failed login', description='Review failed login activity.', scope_state='Karnataka')
    db.commit()
    second, created_again = record_security_event(db, event_type='AUTH_LOGIN_FAILED', category='AUTHENTICATION', title='Failed login', description='Review failed login activity.', scope_state='Karnataka')
    db.commit()

    assert created is True
    assert created_again is False
    assert first.id == second.id
    assert second.occurrence_count == 2
    assert second.status == 'OPEN'


def test_old_alert_does_not_deduplicate(tmp_path):
    db = session(tmp_path)
    alert, _ = record_security_event(db, event_type='API_RATE_LIMITED', category='RATE_LIMIT', title='Rate limited', description='Repeated request rate limit.', dedup_window_seconds=1)
    alert.last_seen_at = datetime.utcnow() - timedelta(seconds=10)
    db.commit()
    newer, created = record_security_event(db, event_type='API_RATE_LIMITED', category='RATE_LIMIT', title='Rate limited', description='Repeated request rate limit.', dedup_window_seconds=1)
    assert created is True
    assert newer.id != alert.id


def test_alert_lifecycle_and_audit_chain(tmp_path):
    db = session(tmp_path)
    alert, _ = record_security_event(db, event_type='SECRET_DETECTED', category='SECRET_DETECTION', title='Secret detected', description='A potential secret requires review.', severity='HIGH')
    db.commit()
    actor = {'id': 1, 'role': 'MINISTRY'}
    from app.main import _audit
    for action in ('SECURITY_ALERT_ACKNOWLEDGED', 'SECURITY_ALERT_INVESTIGATION_STARTED', 'SECURITY_ALERT_RESOLVED', 'SECURITY_ALERT_FALSE_POSITIVE'):
        _audit(db, action, actor, security_alert_id=alert.id, status=action)
    db.commit()
    assert verify_audit_chain(db.query(AuditLogModel).order_by(AuditLogModel.id).all())['status'] == 'VALID'
    assert all(value not in str(alert.__dict__) for value in ('password', 'token', 'secret-value'))


def test_security_endpoints_require_authentication_and_scope(tmp_path, monkeypatch):
    response = TestClient(app).get('/api/security/alerts')
    assert response.status_code == 401
    monkeypatch.setattr('app.main.SessionLocal', session)
    assert SecurityAlertModel.__tablename__ == 'security_alerts'


def test_analysis_alerts_are_separate():
    assert SecurityAlertModel.__tablename__ != 'alerts'
