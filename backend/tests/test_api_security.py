import json
import uuid

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.security import InMemoryRateLimiter


client = TestClient(app)


def test_security_headers_are_present():
    response = client.get('/api/health')

    assert response.status_code == 200
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert response.headers['x-frame-options'] == 'DENY'
    assert response.headers['referrer-policy'] == 'no-referrer'
    assert response.headers['permissions-policy'] == 'camera=(), microphone=(), geolocation=()'


def test_cors_allows_configured_frontend_origin():
    response = client.options('/api/health', headers={
        'Origin': 'http://localhost:5173',
        'Access-Control-Request-Method': 'GET',
    })

    assert response.headers.get('access-control-allow-origin') == 'http://localhost:5173'
    assert response.headers.get('access-control-allow-credentials') == 'true'


def test_cors_does_not_allow_untrusted_origin():
    response = client.options('/api/health', headers={
        'Origin': 'http://untrusted.example',
        'Access-Control-Request-Method': 'GET',
    })

    assert response.headers.get('access-control-allow-origin') != 'http://untrusted.example'


def test_rate_limiter_isolated_and_returns_retry_after():
    limiter = InMemoryRateLimiter(window_seconds=60)

    assert limiter.allow('client-a', 1)[0]
    allowed, retry_after = limiter.allow('client-a', 1)
    assert not allowed
    assert retry_after >= 1
    assert limiter.allow('client-b', 1)[0]


def test_oversized_non_file_request_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, 'max_request_body_mb', 1)
    response = client.post('/api/health', content=b'x' * (1024 * 1024 + 1))

    assert response.status_code == 413
    assert response.json() == {'detail': 'Request body exceeds the maximum allowed size.'}


def test_missing_authentication_still_returns_401():
    response = client.get('/api/dashboard')

    assert response.status_code == 401
    assert response.json() == {'detail': 'Authentication required'}


def test_expensive_endpoint_does_not_bypass_authentication():
    response = client.post('/api/analyze-multi')

    assert response.status_code == 401


def test_login_brute_force_limit_returns_429_without_password_logging():
    identity = f'unknown-{uuid.uuid4().hex}'
    payload = {
        'role': 'MINISTRY',
        'login': identity,
        'identity_id': 'MINISTRY-DEMO',
        'password': 'wrong-password',
    }
    # Lifespan startup creates the schema; this test must not rely on table
    # state left behind by security/upload tests using temporary databases.
    with TestClient(app) as started_client:
        responses = [started_client.post('/api/auth/login', json=payload) for _ in range(6)]

    assert all(response.status_code == 401 for response in responses[:5])
    assert responses[-1].status_code == 429
    assert responses[-1].headers.get('retry-after')
    assert 'wrong-password' not in json.dumps(responses[-1].json())
