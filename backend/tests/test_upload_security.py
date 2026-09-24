import asyncio
from io import BytesIO

import pandas as pd
import pytest
from fastapi import HTTPException, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.models import AuditLogModel
from app.main import _current_user, _secure_upload, app
from app.ml.integrity import hash_file
from app.ml.upload_security import UploadSecurityError, store_upload, validate_file_content


def upload(filename: str, content: bytes, content_type: str = 'application/octet-stream') -> UploadFile:
    return UploadFile(file=BytesIO(content), filename=filename, headers={'content-type': content_type})


def test_valid_csv_is_stored_and_hashed(tmp_path):
    item = upload('projects.csv', b'project_name,state,district,sanction_amount,expenditure\nRoad,Karnataka,Gadag,100,50\n', 'text/csv')
    stored = asyncio.run(store_upload(item, tmp_path, 1024 * 1024))
    validate_file_content(stored, item.content_type, 100, 20)

    assert stored.path.parent == tmp_path.resolve()
    assert stored.storage_name != stored.original_filename
    assert len(hash_file(stored.path)) == 64


def test_valid_xlsx_is_accepted(tmp_path):
    buffer = BytesIO()
    pd.DataFrame([{'project_name': 'Road', 'state': 'Karnataka'}]).to_excel(buffer, index=False)
    item = upload('projects.xlsx', buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    stored = asyncio.run(store_upload(item, tmp_path, 1024 * 1024))

    validate_file_content(stored, item.content_type, 100, 20)


def test_unsupported_extension_is_rejected(tmp_path):
    with pytest.raises(UploadSecurityError, match='Unsupported or invalid file type'):
        asyncio.run(store_upload(upload('malicious.exe', b'MZ'), tmp_path, 1024 * 1024))


def test_path_traversal_filename_is_rejected(tmp_path):
    with pytest.raises(UploadSecurityError, match='Invalid filename'):
        asyncio.run(store_upload(upload('../../test.csv', b'a,b\n1,2\n'), tmp_path, 1024 * 1024))


def test_long_filename_is_rejected(tmp_path):
    with pytest.raises(UploadSecurityError, match='Invalid filename'):
        asyncio.run(store_upload(upload('a' * 256 + '.csv', b'a,b\n1,2\n'), tmp_path, 1024 * 1024))


def test_oversized_upload_is_rejected(tmp_path):
    with pytest.raises(UploadSecurityError, match='maximum allowed upload size'):
        asyncio.run(store_upload(upload('large.csv', b'a' * 11), tmp_path, 10))


def test_fake_xlsx_content_is_rejected(tmp_path):
    item = upload('fake.xlsx', b'not an excel workbook')
    stored = asyncio.run(store_upload(item, tmp_path, 1024 * 1024))

    with pytest.raises(UploadSecurityError, match='Unsupported or invalid file type'):
        validate_file_content(stored, item.content_type, 100, 20)


def test_malformed_csv_content_is_rejected(tmp_path):
    item = upload('malformed.csv', b'\x00\x01\x02')
    stored = asyncio.run(store_upload(item, tmp_path, 1024 * 1024))

    with pytest.raises(UploadSecurityError, match='Unsupported or invalid file type'):
        validate_file_content(stored, item.content_type, 100, 20)


def test_macro_enabled_extension_is_rejected(tmp_path):
    with pytest.raises(UploadSecurityError, match='Unsupported or invalid file type'):
        asyncio.run(store_upload(upload('macro.xlsm', b'content'), tmp_path, 1024 * 1024))


def test_secure_upload_rejection_creates_audit_event(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'security.db'}")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    token = _current_user.set({'id': 1, 'role': 'MINISTRY', 'scope_type': 'NATIONAL'})
    try:
        with pytest.raises(HTTPException) as error:
            asyncio.run(_secure_upload(upload('blocked.exe', b'MZ'), session))
    finally:
        _current_user.reset(token)

    assert error.value.status_code == 400
    assert session.query(AuditLogModel).one().action == 'DATASET_UPLOAD_REJECTED_TYPE'


def test_upload_endpoint_requires_authentication():
    response = TestClient(app).post('/api/upload', files={'files': ('projects.csv', b'a,b\n1,2\n', 'text/csv')})

    assert response.status_code == 401
