from datetime import datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import has_permission
from app.database.base import Base
from app.database.models import AuditLogModel
from app.main import _audit, app
from app.ml.audit_integrity import verify_audit_chain


def make_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'audit.db'}")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_new_audit_records_form_a_hash_chain(tmp_path):
    session = make_session(tmp_path)
    first = _audit(session, 'FIRST_EVENT', {'id': 1, 'role': 'MINISTRY'}, detail='one')
    session.commit()
    second = _audit(session, 'SECOND_EVENT', {'id': 1, 'role': 'MINISTRY'}, detail='two')
    session.commit()
    third = _audit(session, 'THIRD_EVENT', {'id': 1, 'role': 'MINISTRY'}, detail='three')
    session.commit()

    assert first.record_hash
    assert first.previous_hash is None
    assert second.previous_hash == first.record_hash
    assert third.previous_hash == second.record_hash
    assert verify_audit_chain(session.query(AuditLogModel).order_by(AuditLogModel.id).all())['status'] == 'VALID'


def test_modified_audit_field_is_detected(tmp_path):
    session = make_session(tmp_path)
    record = _audit(session, 'ORIGINAL', {'id': 1, 'role': 'MINISTRY'})
    session.commit()
    record.action = 'MODIFIED'
    session.commit()

    result = verify_audit_chain(session.query(AuditLogModel).order_by(AuditLogModel.id).all())

    assert result['status'] == 'FAILED'
    assert result['first_failure'] == {'audit_log_id': record.id, 'reason': 'RECORD_HASH_MISMATCH'}


def test_modified_previous_hash_is_detected(tmp_path):
    session = make_session(tmp_path)
    _audit(session, 'FIRST', {'id': 1, 'role': 'MINISTRY'})
    session.commit()
    second = _audit(session, 'SECOND', {'id': 1, 'role': 'MINISTRY'})
    session.commit()
    second.previous_hash = '0' * 64
    session.commit()

    result = verify_audit_chain(session.query(AuditLogModel).order_by(AuditLogModel.id).all())

    assert result['status'] == 'FAILED'
    assert result['first_failure']['reason'] == 'CHAIN_BROKEN'


def test_deleted_record_breaks_the_chain(tmp_path):
    session = make_session(tmp_path)
    _audit(session, 'FIRST', {'id': 1, 'role': 'MINISTRY'})
    session.commit()
    middle = _audit(session, 'MIDDLE', {'id': 1, 'role': 'MINISTRY'})
    session.commit()
    _audit(session, 'THIRD', {'id': 1, 'role': 'MINISTRY'})
    session.commit()
    session.delete(middle)
    session.commit()

    result = verify_audit_chain(session.query(AuditLogModel).order_by(AuditLogModel.id).all())

    assert result['status'] == 'FAILED'
    assert result['first_failure']['reason'] == 'CHAIN_BROKEN'


def test_legacy_records_are_not_reported_as_valid(tmp_path):
    session = make_session(tmp_path)
    session.add(AuditLogModel(action='LEGACY', metadata_json={}, created_at=datetime.utcnow()))
    session.commit()

    result = verify_audit_chain(session.query(AuditLogModel).order_by(AuditLogModel.id).all())

    assert result['status'] == 'INTEGRITY_CHECK_NOT_AVAILABLE'
    assert result['first_failure']['reason'] == 'HASH_NOT_AVAILABLE'


def test_empty_chain_is_valid(tmp_path):
    session = make_session(tmp_path)

    assert verify_audit_chain([])['status'] == 'VALID'


def test_integrity_permission_is_ministry_only():
    assert has_permission({'role': 'MINISTRY'}, 'audit:integrity')
    assert not has_permission({'role': 'STATE_NODAL_AUTHORITY'}, 'audit:integrity')
    assert not has_permission({'role': 'DISTRICT_AUTHORITY'}, 'audit:integrity')
    assert not has_permission({'role': 'MEMBER_OF_PARLIAMENT'}, 'audit:integrity')


def test_integrity_endpoint_requires_authentication():
    response = TestClient(app).get('/api/auth/audit-log/integrity')

    assert response.status_code == 401
