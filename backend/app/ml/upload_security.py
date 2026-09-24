from __future__ import annotations

import re
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from fastapi import UploadFile

from app.ml.preprocessing import read_file_to_dataframe


ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}
MAX_FILENAME_LENGTH = 255
CHUNK_SIZE = 1024 * 1024
_BLOCKED_CONTENT_TYPES = {
    'application/x-msdownload',
    'application/x-sh',
    'application/x-httpd-php',
    'text/html',
    'application/javascript',
}


@dataclass(frozen=True)
class StoredUpload:
    original_filename: str
    storage_name: str
    path: Path
    extension: str
    size_bytes: int


class UploadSecurityError(ValueError):
    def __init__(self, message: str, action: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.action = action
        self.status_code = status_code


def validate_filename(filename: str | None) -> tuple[str, str]:
    name = str(filename or '')
    if not name or len(name) > MAX_FILENAME_LENGTH or '\x00' in name:
        raise UploadSecurityError('Invalid filename.', 'DATASET_UPLOAD_REJECTED_FILENAME')
    if any(character in name for character in '/\\') or '..' in name:
        raise UploadSecurityError('Invalid filename.', 'DATASET_UPLOAD_REJECTED_FILENAME')
    if any(ord(character) < 32 for character in name):
        raise UploadSecurityError('Invalid filename.', 'DATASET_UPLOAD_REJECTED_FILENAME')
    extension = Path(name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise UploadSecurityError('Unsupported or invalid file type.', 'DATASET_UPLOAD_REJECTED_TYPE')
    return name, extension


def _validate_content_type(content_type: str | None) -> None:
    if content_type and content_type.casefold() in _BLOCKED_CONTENT_TYPES:
        raise UploadSecurityError('Unsupported or invalid file type.', 'DATASET_UPLOAD_REJECTED_TYPE')


def _validate_csv(path: Path, max_rows: int, max_columns: int) -> None:
    try:
        sample = path.read_bytes()[:CHUNK_SIZE]
        if not sample or b'\x00' in sample:
            raise ValueError('binary CSV content')
        sample.decode('utf-8-sig')
        frame = pd.read_csv(path, nrows=max_rows + 1, on_bad_lines='error')
    except (OSError, UnicodeError, ValueError, pd.errors.ParserError) as exc:
        raise UploadSecurityError('Unsupported or invalid file type.', 'DATASET_UPLOAD_REJECTED_CONTENT') from exc
    if len(frame) > max_rows or len(frame.columns) > max_columns:
        raise UploadSecurityError('Dataset exceeds the supported row or column limit.', 'DATASET_UPLOAD_REJECTED_DIMENSIONS')


def _validate_excel(path: Path, extension: str, max_rows: int, max_columns: int) -> None:
    try:
        if extension == '.xlsx':
            if not zipfile.is_zipfile(path):
                raise ValueError('invalid XLSX container')
            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
                if '[Content_Types].xml' not in names or 'xl/workbook.xml' not in names:
                    raise ValueError('invalid XLSX workbook')
                if any(name.casefold().endswith('vbaproject.bin') for name in names):
                    raise ValueError('macro-enabled workbook')
        else:
            signature = path.read_bytes()[:8]
            if signature != b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
                raise ValueError('invalid XLS container')
        frame = read_file_to_dataframe(path)
    except (OSError, ValueError, ImportError, zipfile.BadZipFile, pd.errors.ParserError) as exc:
        raise UploadSecurityError('Unsupported or invalid file type.', 'DATASET_UPLOAD_REJECTED_CONTENT') from exc
    if len(frame) > max_rows or len(frame.columns) > max_columns:
        raise UploadSecurityError('Dataset exceeds the supported row or column limit.', 'DATASET_UPLOAD_REJECTED_DIMENSIONS')


def validate_file_content(upload: StoredUpload, content_type: str | None, max_rows: int, max_columns: int) -> None:
    _validate_content_type(content_type)
    if upload.extension == '.csv':
        _validate_csv(upload.path, max_rows, max_columns)
    else:
        _validate_excel(upload.path, upload.extension, max_rows, max_columns)


async def store_upload(file: UploadFile, upload_dir: str | Path, max_size_bytes: int) -> StoredUpload:
    original_filename, extension = validate_filename(file.filename)
    root = Path(upload_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    storage_name = f'{uuid.uuid4().hex}{extension}'
    path = (root / storage_name).resolve()
    if path.parent != root:
        raise UploadSecurityError('Unable to safely store this file.', 'DATASET_UPLOAD_REJECTED_PATH', 400)
    size = 0
    try:
        file.file.seek(0)
        with path.open('xb') as destination:
            while chunk := file.file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > max_size_bytes:
                    raise UploadSecurityError('File exceeds the maximum allowed upload size.', 'DATASET_UPLOAD_REJECTED_SIZE', 413)
                destination.write(chunk)
    except UploadSecurityError:
        path.unlink(missing_ok=True)
        raise
    except (OSError, ValueError) as exc:
        path.unlink(missing_ok=True)
        raise UploadSecurityError('Unable to safely store this file.', 'DATASET_UPLOAD_REJECTED_STORAGE') from exc
    return StoredUpload(original_filename, storage_name, path, extension, size)
