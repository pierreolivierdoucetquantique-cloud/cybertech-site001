"""
Protection contre les attaques brute-force sur les connexions.
Compteur en mémoire par IP + email (suffisant pour une instance unique Render).
"""
import time
from collections import defaultdict

MAX_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60  # 15 minutes
LOCKOUT_SECONDS = 15 * 60

_attempts: dict[str, list[float]] = defaultdict(list)
_locked_until: dict[str, float] = {}


def _key(identifier: str, ip: str) -> str:
    return f"{identifier.lower()}|{ip}"


def is_locked(identifier: str, ip: str) -> tuple[bool, int]:
    """Retourne (is_locked, seconds_remaining)."""
    k = _key(identifier, ip)
    until = _locked_until.get(k)
    if until and until > time.time():
        return True, int(until - time.time())
    return False, 0


def record_failed_attempt(identifier: str, ip: str) -> None:
    k = _key(identifier, ip)
    now = time.time()
    _attempts[k] = [t for t in _attempts[k] if now - t < WINDOW_SECONDS]
    _attempts[k].append(now)
    if len(_attempts[k]) >= MAX_ATTEMPTS:
        _locked_until[k] = now + LOCKOUT_SECONDS
        _attempts[k] = []


def reset_attempts(identifier: str, ip: str) -> None:
    k = _key(identifier, ip)
    _attempts.pop(k, None)
    _locked_until.pop(k, None)
