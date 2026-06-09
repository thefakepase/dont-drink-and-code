"""Token di sobrietà firmato HMAC e cooldown dopo i fallimenti.

Il token vive in ~/.sobergate/ (override con SOBERGATE_HOME, utile nei test).
La firma impedisce di fabbricare un token a mano — o di farselo
fabbricare da un'AI — senza superare davvero il test.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import socket
import time
from pathlib import Path

SECRET_FILE = "secret.key"
TOKEN_FILE = "token.json"
COOLDOWN_FILE = "cooldown.json"

DEFAULT_HOURS = 10.0
FAIL_COOLDOWN_MIN = 30.0


def home_dir() -> Path:
    return Path(os.environ.get("SOBERGATE_HOME", str(Path.home() / ".sobergate")))


def _secret() -> bytes:
    d = home_dir()
    d.mkdir(parents=True, exist_ok=True)
    f = d / SECRET_FILE
    if not f.exists():
        f.write_bytes(secrets.token_bytes(32))
        try:
            os.chmod(f, 0o600)
        except OSError:
            pass
    return f.read_bytes()


def _sign(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(_secret(), canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def issue(score: int, hours: float = DEFAULT_HOURS) -> dict:
    now = time.time()
    payload = {
        "v": 1,
        "issued": now,
        "expires": now + hours * 3600.0,
        "score": score,
        "host": socket.gethostname(),
    }
    token = {"payload": payload, "sig": _sign(payload)}
    (home_dir() / TOKEN_FILE).write_text(json.dumps(token, indent=2), encoding="utf-8")
    return payload


def status():
    """Ritorna (stato, payload). Stati: valid, expired, tampered, missing."""
    f = home_dir() / TOKEN_FILE
    if not f.exists():
        return "missing", None
    try:
        token = json.loads(f.read_text(encoding="utf-8"))
        payload, sig = token["payload"], token["sig"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return "tampered", None
    if not hmac.compare_digest(sig, _sign(payload)):
        return "tampered", None
    if time.time() >= payload.get("expires", 0):
        return "expired", payload
    return "valid", payload


def revoke() -> None:
    f = home_dir() / TOKEN_FILE
    if f.exists():
        f.unlink()


def start_cooldown(minutes: float = FAIL_COOLDOWN_MIN) -> None:
    d = home_dir()
    d.mkdir(parents=True, exist_ok=True)
    data = {"retry_after": time.time() + minutes * 60.0}
    (d / COOLDOWN_FILE).write_text(json.dumps(data), encoding="utf-8")


def cooldown_remaining() -> float:
    """Secondi che mancano prima di poter ritentare il test (0 se libero)."""
    f = home_dir() / COOLDOWN_FILE
    if not f.exists():
        return 0.0
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
        return max(0.0, float(data.get("retry_after", 0)) - time.time())
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0.0
