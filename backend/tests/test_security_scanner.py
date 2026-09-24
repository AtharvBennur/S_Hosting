from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from app.ml.upload_security import StoredUpload
from app.security_scanner import scan_dependencies, scan_source_tree, scan_upload


def stored(tmp_path, filename, content):
    path = tmp_path / 'stored'
    path.write_bytes(content)
    return StoredUpload(filename, 'uuid' + path.suffix, path, path.suffix.lower(), len(content))


def test_safe_csv_is_clean(tmp_path):
    result = scan_upload(stored(tmp_path, 'projects.csv', b'project_name,state\nRoad,Karnataka\n'), 'text/csv')
    assert result.status == 'CLEAN'


def test_safe_xlsx_is_clean(tmp_path):
    buffer = BytesIO()
    pd.DataFrame([{'project_name': 'Road'}]).to_excel(buffer, index=False)
    result = scan_upload(stored(tmp_path, 'projects.xlsx', buffer.getvalue()), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    assert result.status == 'CLEAN'


def test_executable_script_and_double_extension_are_detected(tmp_path):
    assert scan_upload(stored(tmp_path, 'payload.exe', b'MZ'), None).status == 'BLOCKED'
    assert scan_upload(stored(tmp_path, 'payload.csv', b'#!/bin/sh\necho unsafe'), 'text/csv').status == 'SUSPICIOUS'
    assert scan_upload(stored(tmp_path, 'payload.exe.csv', b'a,b\n1,2'), 'text/csv').detection_category == 'DOUBLE_EXTENSION'


def test_macro_embedded_object_and_malformed_office_are_safe(tmp_path):
    macro = BytesIO()
    with ZipFile(macro, 'w') as archive:
        archive.writestr('xl/vbaProject.bin', b'not executed')
    assert scan_upload(stored(tmp_path, 'macro.xlsx', macro.getvalue()), None).status == 'BLOCKED'
    embedded = BytesIO()
    with ZipFile(embedded, 'w') as archive:
        archive.writestr('xl/embeddings/object.bin', b'object')
    assert scan_upload(stored(tmp_path, 'embedded.xlsx', embedded.getvalue()), None).status == 'SUSPICIOUS'
    assert scan_upload(stored(tmp_path, 'broken.xlsx', b'not a zip'), None).status == 'BLOCKED'


def test_scanner_does_not_return_raw_content_or_execute(tmp_path):
    result = scan_upload(stored(tmp_path, 'secret.csv', b'api_key=super-secret-value'), 'text/csv')
    assert 'super-secret-value' not in str(result.as_dict())
    assert result.status == 'CLEAN'


def test_source_scan_masks_secrets_and_dependency_unavailability_is_safe(tmp_path):
    (tmp_path / 'source.py').write_text("password = 'this-is-not-returned'\n", encoding='utf-8')
    findings = scan_source_tree(tmp_path)
    assert findings[0]['masked'] == '[REDACTED]'
    assert 'this-is-not-returned' not in str(findings)
    result = scan_dependencies(tmp_path / 'requirements.txt')
    assert result['findings'] == []