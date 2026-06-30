"""
Utilitaires de sécurité : hash des mots de passe (bcrypt) et JWT.

Principes appliqués :
- Les mots de passe ne sont JAMAIS stockés en clair, seulement leur hash bcrypt.
- Les tokens JWT contiennent un "jti" (identifiant unique) vérifié contre la
  table de sessions en base — ça permet de RÉVOQUER une session avant son
  expiration naturelle (ex: déconnexion, changement de mot de passe, suppression
  de compte), ce qu'un JWT seul ne permet pas de faire.
"""
import uuid
import datetime as dt
from typing import Optional

from passlib.context import CryptContext
from jose import jwt, JWTError

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(plain_password, password_hash)
    except Exception:
        return False


def create_access_token(subject: str, expires_minutes: int, extra_claims: Optional[dict] = None) -> tuple[str, str, dt.datetime]:
    """
    Crée un JWT signé.
    Retourne (token, jti, expires_at) pour que l'appelant puisse enregistrer
    la session correspondante en base de données.
    """
    now = dt.datetime.utcnow()
    expires_at = now + dt.timedelta(minutes=expires_minutes)
    jti = str(uuid.uuid4())

    payload = {
        "sub": subject,
        "iat": now,
        "exp": expires_at,
        "jti": jti,
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def decode_token(token: str) -> Optional[dict]:
    """Décode et valide un JWT. Retourne None si invalide/expiré."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
