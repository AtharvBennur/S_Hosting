"""Non-executing security checks for uploaded files and project sources."""
from __future__ import annotations

import re
import json
import subprocess
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

from app.ml.upload_security import StoredUpload


SCANNER_NAME = 'internal-security-scanner'
SCANNER_VERSION = '1.0'
_SCRIPT_MARKERS = (b'#!', b'<script', b'<?php', b'powershell -', b'cmd.exe /c')
_EXECUTABLE_SIGNATURES = (b'MZ', b'\x7fELF', b'\xca\xfe\xba\xbe')
_SECRET_PATTERNS = {
    'private_key': re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    'api_key': re.compile(r'(?i)\b(api[_-]?key|access[_-]?token)\s*[:=]\s*["\'][^"\']{12,}'),
    'password': re.compile(r'(?i)\b(password|passwd|secret)\s*[:=]\s*["\'][^"\']{8,}'),
}


@dataclass(frozen=True)
class SecurityScanResult:
    status: str
    severity: str
    detection_category: str | None = None
    safe_summary: str = ''
    scanner: str = SCANNER_NAME
    scanner_version: str = SCANNER_VERSION

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _result(status: str, severity: str, category: str | None = None, summary: str = '') -> SecurityScanResult:
    return SecurityScanResult(status, severity, category, summary)


def _filename_result(filename: str) -> SecurityScanResult | None:
    if '\x00' in filename or '/' in filename or '\\' in filename or '..' in filename or any(ord(character) < 32 for character in filename):
        return _result('BLOCKED', 'HIGH', 'INVALID_FILENAME', 'Filename contains a control character.')
    suffixes = [f'.{suffix.casefold()}' for suffix in Path(filename).name.split('.')[-3:] if suffix]
    dangerous = {'.exe', '.dll', '.bat', '.cmd', '.ps1', '.sh', '.js', '.html', '.php', '.zip', '.rar', '.7z'}
    if len(suffixes) >= 2 and any(suffix in dangerous for suffix in suffixes[:-1]):
        return _result('SUSPICIOUS', 'HIGH', 'DOUBLE_EXTENSION', 'Filename contains a dangerous double-extension pattern.')
    return None


def scan_upload(upload: StoredUpload, content_type: str | None = None) -> SecurityScanResult:
    """Scan an already Stage-3-validated file without executing or extracting it."""
    filename_result = _filename_result(upload.original_filename)
    if filename_result:
        return filename_result
    try:
        with upload.path.open('rb') as source:
            sample = source.read(1024 * 1024)
    except OSError:
        return _result('SCAN_ERROR', 'HIGH', 'READ_ERROR', 'The file could not be read by the scanner.')
    if sample.startswith(_EXECUTABLE_SIGNATURES):
        return _result('BLOCKED', 'CRITICAL', 'EXECUTABLE_SIGNATURE', 'Executable file signature detected.')
    lowered = sample.lower()
    if any(marker in lowered for marker in _SCRIPT_MARKERS):
        return _result('SUSPICIOUS', 'HIGH', 'SCRIPT_CONTENT', 'Script-like content detected in the uploaded file.')
    extension = upload.extension or Path(upload.original_filename).suffix.casefold()
    if extension == '.xlsx':
        try:
            with zipfile.ZipFile(upload.path) as archive:
                names = [name.casefold() for name in archive.namelist()]
                if any(name.endswith('vbaproject.bin') for name in names):
                    return _result('BLOCKED', 'HIGH', 'OFFICE_MACRO', 'Office macro payload detected.')
                if any('/embeddings/' in name or name.startswith('embeddings/') for name in names):
                    return _result('SUSPICIOUS', 'MEDIUM', 'EMBEDDED_OBJECT', 'Embedded Office object detected.')
                if any(info.file_size > 100 * 1024 * 1024 or (info.compress_size and info.file_size / info.compress_size > 1000) for info in archive.infolist()):
                    return _result('BLOCKED', 'HIGH', 'CONTAINER_EXPANSION', 'Unsafe container expansion ratio detected.')
        except (OSError, zipfile.BadZipFile, ValueError):
            return _result('BLOCKED', 'HIGH', 'MALFORMED_CONTAINER', 'Office container could not be safely inspected.')
    return _result('CLEAN', 'NONE', summary='Configured internal checks found no supported suspicious indicators.')


def scan_dependencies(requirements: Path, package_lock: Path | None = None) -> dict[str, Any]:
    """Return metadata for optional ecosystem scanners without fabricating findings."""
    tools: list[str] = []
    findings: list[dict[str, Any]] = []
    if requirements.exists():
        try:
            result = subprocess.run(['pip-audit', '-r', str(requirements), '--format', 'json'], check=False, capture_output=True, text=True, timeout=60)
            tools.append('pip-audit')
            if result.stdout:
                try:
                    for item in json.loads(result.stdout):
                        findings.append({
                            'package': item.get('name'),
                            'installed_version': item.get('version'),
                            'advisory_id': (item.get('id') or (item.get('ids') or [None])[0]),
                            'severity': 'UNKNOWN',
                            'summary': item.get('description', 'Advisory reported by pip-audit.'),
                            'recommended_remediation': item.get('fix_versions', []),
                        })
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
        except (OSError, subprocess.SubprocessError):
            pass
    if package_lock and package_lock.exists():
        try:
            result = subprocess.run(['npm', 'audit', '--json'], cwd=str(package_lock.parent), check=False, capture_output=True, text=True, timeout=60)
            tools.append('npm audit')
            if result.stdout:
                try:
                    report = json.loads(result.stdout)
                    for name, item in (report.get('vulnerabilities') or {}).items():
                        advisories = item.get('via') or []
                        first = advisories[0] if advisories and isinstance(advisories[0], dict) else {}
                        findings.append({
                            'package': name,
                            'installed_version': None,
                            'advisory_id': first.get('url') or first.get('source'),
                            'severity': item.get('severity', 'UNKNOWN').upper(),
                            'summary': first.get('title', 'Advisory reported by npm audit.'),
                            'recommended_remediation': item.get('fixAvailable'),
                        })
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
        except (OSError, subprocess.SubprocessError):
            pass
    return {'status': 'COMPLETED' if tools else 'SCAN_NOT_AVAILABLE', 'tools_attempted': tools, 'findings': findings}


def scan_source_tree(root: Path) -> list[dict[str, Any]]:
    """Find likely committed secrets while returning only masked metadata."""
    findings: list[dict[str, Any]] = []
    excluded = {'.env.example', 'test_security_scanner.py'}
    for path in root.rglob('*'):
        if not path.is_file() or path.name in excluded or any(part in {'.git', '.venv', 'node_modules', 'dist'} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            for category, pattern in _SECRET_PATTERNS.items():
                if pattern.search(line):
                    findings.append({'path': str(path), 'line': line_number, 'category': category, 'severity': 'HIGH', 'masked': '[REDACTED]'})
    return findings