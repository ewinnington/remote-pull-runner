import os
import json
import base64
import uuid
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

# Files for storing keys and encrypted secrets
KEYS_FILE = 'keys.json'
SECRETS_FILE = 'secrets.json'


def _ensure_file(path, default):
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump(default, f, indent=2)
        os.chmod(path, 0o700)


def load_keys():
    _ensure_file(KEYS_FILE, {})
    with open(KEYS_FILE, 'r') as f:
        data = json.load(f)
    # Generate keys on first run
    changed = False
    if 'api_key' not in data:
        data['api_key'] = uuid.uuid4().hex
        changed = True
    if 'encryption_key' not in data:
        data['encryption_key'] = base64.urlsafe_b64encode(Fernet.generate_key()).decode()
        changed = True
    if changed:
        with open(KEYS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    return data


def _derive_fernet_key(encryption_key: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(encryption_key))


def _load_secrets():
    _ensure_file(SECRETS_FILE, [])
    with open(SECRETS_FILE, 'r') as f:
        return json.load(f)


def _save_secrets(records):
    with open(SECRETS_FILE, 'w') as f:
        json.dump(records, f, indent=2)
    #os.chmod(SECRETS_FILE, 0o700)


def store_secret(name: str, plaintext: str) -> str:
    keys = load_keys()
    enc_key = base64.urlsafe_b64decode(keys['encryption_key'].encode())
    salt = os.urandom(16)
    fkey = _derive_fernet_key(enc_key, salt)
    f = Fernet(fkey)
    token = f.encrypt(plaintext.encode())
    record = {
        'id': uuid.uuid4().hex,
        'name': name,
        'salt': base64.b64encode(salt).decode(),
        'encrypted_data': base64.b64encode(token).decode()
    }
    records = _load_secrets()
    records.append(record)
    _save_secrets(records)
    return record['id']


def get_secret(secret_id: str) -> str:
    keys = load_keys()
    enc_key = base64.urlsafe_b64decode(keys['encryption_key'].encode())
    records = _load_secrets()
    rec = next((r for r in records if r['id'] == secret_id), None)
    if not rec:
        raise KeyError(f"Secret {secret_id} not found")
    salt = base64.b64decode(rec['salt'].encode())
    token = base64.b64decode(rec['encrypted_data'].encode())
    fkey = _derive_fernet_key(enc_key, salt)
    f = Fernet(fkey)
    return f.decrypt(token).decode()


def mask_secret(plaintext: str) -> str:
    tail = plaintext[-3:] if len(plaintext) >= 3 else "***"
    return '*'*8 + tail


def delete_secret(secret_id: str):
    records = _load_secrets()
    filtered = [r for r in records if r['id'] != secret_id]
    if len(filtered) != len(records):
        _save_secrets(filtered)
