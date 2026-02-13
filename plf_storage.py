import os
import secrets
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

PLF_MAGIC = b"PLF1"
SALT_SIZE = 16
NONCE_SIZE = 12
KDF_ITERATIONS = 200_000
KEY_SIZE = 32


def _derive_key(password: str, salt: bytes) -> bytes:
    if not isinstance(password, str) or not password:
        raise ValueError("Mot de passe requis")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_bytes(data: bytes, password: str) -> bytes:
    salt = secrets.token_bytes(SALT_SIZE)
    key = _derive_key(password, salt)
    nonce = secrets.token_bytes(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return PLF_MAGIC + salt + nonce + ciphertext


def decrypt_bytes(data: bytes, password: str) -> bytes:
    if not data.startswith(PLF_MAGIC):
        raise ValueError("Format PLF invalide")
    offset = len(PLF_MAGIC)
    salt = data[offset:offset + SALT_SIZE]
    offset += SALT_SIZE
    nonce = data[offset:offset + NONCE_SIZE]
    offset += NONCE_SIZE
    ciphertext = data[offset:]
    key = _derive_key(password, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


def write_plf_from_sqlite(sqlite_path: str, plf_path: str, password: str) -> None:
    with open(sqlite_path, "rb") as f:
        plaintext = f.read()
    encrypted = encrypt_bytes(plaintext, password)
    with open(plf_path, "wb") as f:
        f.write(encrypted)


def decrypt_plf_to_sqlite(plf_path: str, sqlite_path: str, password: str) -> None:
    with open(plf_path, "rb") as f:
        data = f.read()
    plaintext = decrypt_bytes(data, password)
    with open(sqlite_path, "wb") as f:
        f.write(plaintext)


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def temp_sqlite_path(temp_dir: str) -> str:
    ensure_dir(temp_dir)
    name = secrets.token_hex(8)
    return os.path.join(temp_dir, f"plf_{name}.db")
