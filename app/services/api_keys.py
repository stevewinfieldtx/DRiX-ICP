import hashlib
import secrets

from passlib.context import CryptContext

_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_key() -> tuple[str, str, str]:
    """Return (raw_key, prefix, hashed_key). Raw is shown to the user once."""
    body = secrets.token_urlsafe(24)
    raw = f"fs_live_{body}"
    prefix = raw[:12]
    hashed = _ctx.hash(raw)
    return raw, prefix, hashed


def verify_key(raw: str, hashed: str) -> bool:
    return _ctx.verify(raw, hashed)


def fingerprint(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
