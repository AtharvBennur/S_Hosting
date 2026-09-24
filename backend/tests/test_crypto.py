import base64
import json

import pytest

from app.crypto import EncryptedValueError, EncryptionConfigurationError, decrypt_value, encrypt_value


def key(seed: int = 1) -> str:
    return base64.urlsafe_b64encode(bytes([seed]) * 32).decode().rstrip('=')


def environment(version: str = 'v1', keys: str | None = None) -> dict[str, str]:
    values = {'APP_ENCRYPTION_KEY_VERSION': version}
    if keys is None:
        values['APP_ENCRYPTION_KEY'] = key(1)
    else:
        values['APP_ENCRYPTION_KEYS'] = keys
    return values


def test_aes256_gcm_round_trip_and_plaintext_is_not_exposed():
    plaintext = 'confidential application value'
    envelope = encrypt_value(plaintext, environment())

    assert decrypt_value(envelope, environment()) == plaintext.encode()
    assert plaintext not in envelope
    assert json.loads(envelope)['algorithm'] == 'AES-256-GCM'


def test_each_encryption_uses_a_fresh_nonce():
    first = json.loads(encrypt_value('same value', environment()))
    second = json.loads(encrypt_value('same value', environment()))

    assert first['nonce'] != second['nonce']
    assert first['ciphertext'] != second['ciphertext']


def test_wrong_key_and_tampering_fail_authentication():
    envelope = encrypt_value('secret', environment())
    payload = json.loads(envelope)
    payload['ciphertext'] = payload['ciphertext'][:-1] + ('A' if payload['ciphertext'][-1] != 'A' else 'B')

    with pytest.raises(EncryptedValueError):
        decrypt_value(envelope, environment(keys=f'v1:{key(2)}'))
    with pytest.raises(EncryptedValueError):
        decrypt_value(json.dumps(payload), environment())


def test_tampered_nonce_fails():
    payload = json.loads(encrypt_value('secret', environment()))
    payload['nonce'] = key(2)[:16]

    with pytest.raises(EncryptedValueError):
        decrypt_value(json.dumps(payload), environment())


@pytest.mark.parametrize('envelope', ['', '{}', '{"version":"v1","algorithm":"wrong"}', 'not-json'])
def test_malformed_or_unsupported_envelope_fails(envelope):
    with pytest.raises(EncryptedValueError):
        decrypt_value(envelope, environment())


def test_key_version_rotation_and_historical_decryption():
    old = key(1)
    new = key(2)
    old_envelope = encrypt_value('old', environment(keys=f'v1:{old}'))
    new_envelope = encrypt_value('new', environment(version='v2', keys=f'v1:{old},v2:{new}'))

    assert decrypt_value(old_envelope, environment(version='v2', keys=f'v1:{old},v2:{new}')) == b'old'
    assert decrypt_value(new_envelope, environment(version='v2', keys=f'v1:{old},v2:{new}')) == b'new'
    assert json.loads(new_envelope)['version'] == 'v2'


@pytest.mark.parametrize('values', [
    {},
    {'APP_ENCRYPTION_KEY_VERSION': 'v1'},
    {'APP_ENCRYPTION_KEY_VERSION': 'v1', 'APP_ENCRYPTION_KEY': 'too-short'},
    {'APP_ENCRYPTION_KEY_VERSION': 'v2', 'APP_ENCRYPTION_KEYS': f'v1:{key(1)}'},
    {'APP_ENCRYPTION_KEY_VERSION': 'v1', 'APP_ENCRYPTION_KEYS': f'v1:{key(1)},v1:{key(2)}'},
])
def test_missing_or_invalid_key_configuration_fails_closed(values):
    with pytest.raises(EncryptionConfigurationError):
        encrypt_value('secret', values)


def test_missing_historical_key_fails_without_exposing_key_material():
    old = key(1)
    envelope = encrypt_value('secret', environment(keys=f'v1:{old}'))

    with pytest.raises(EncryptedValueError) as error:
        decrypt_value(envelope, environment(version='v2', keys=f'v2:{key(2)}'))
    assert old not in str(error.value)
    assert key(2) not in str(error.value)


def test_keys_are_not_returned_by_api_or_exceptions():
    secret = key(1)
    envelope = encrypt_value('secret', environment())

    assert secret not in envelope
    with pytest.raises(EncryptedValueError) as error:
        decrypt_value(envelope, environment(keys=f'v1:{key(2)}'))
    assert secret not in str(error.value)
