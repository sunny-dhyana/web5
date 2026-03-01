import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_KEYS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "keys",
)


def _init_keys() -> None:
    os.makedirs(_KEYS_DIR, exist_ok=True)
    default_path = os.path.join(_KEYS_DIR, "default.key")
    with open(default_path, "w") as f:
        f.write(settings.secret_key + "\n")


_init_keys()


def _load_signing_key(kid: str) -> str:
    key_path = os.path.join(_KEYS_DIR, kid)
    with open(key_path, "r") as f:
        return f.read().strip()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm,
                      headers={"kid": "default"})


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm,
                      headers={"kid": "default"})


def decode_token(token: str) -> Optional[dict]:
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid", "default")
        if kid == "default":
            signing_key = settings.secret_key
        else:
            signing_key = _load_signing_key(kid)
        payload = jwt.decode(token, signing_key, algorithms=[settings.algorithm])
        return payload
    except Exception:
        return None


def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)
