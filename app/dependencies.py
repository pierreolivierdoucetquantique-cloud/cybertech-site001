"""
Dépendances FastAPI pour l'authentification.

Vérifie le JWT présent dans un cookie HttpOnly, ET vérifie que la session
correspondante existe encore en base et n'a pas été révoquée — ce qui permet
une déconnexion / suppression de compte immédiate et réelle (un JWT seul
resterait valide jusqu'à son expiration naturelle).
"""
import datetime as dt
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.utils.security import decode_token
from app.models.client import Client, ClientSession
from app.models.admin import Admin, AdminSession


def get_current_client(request: Request, db: Session = Depends(get_db)) -> Client:
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié.")

    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée.")

    jti = payload.get("jti")
    client_id = payload.get("sub")

    session = (
        db.query(ClientSession)
        .filter(ClientSession.token_id == jti, ClientSession.revoked == False)  # noqa: E712
        .first()
    )
    if not session or session.expires_at < dt.datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée.")

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client or not client.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte introuvable ou désactivé.")

    return client


def get_optional_client(request: Request, db: Session = Depends(get_db)) -> Optional[Client]:
    """Comme get_current_client, mais retourne None plutôt qu'une erreur si non connecté."""
    try:
        return get_current_client(request, db)
    except HTTPException:
        return None


def get_current_admin(request: Request, db: Session = Depends(get_db)) -> Admin:
    token = request.cookies.get(settings.ADMIN_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié.")

    payload = decode_token(token)
    if not payload or payload.get("scope") != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée.")

    jti = payload.get("jti")
    admin_id = payload.get("sub")

    session = (
        db.query(AdminSession)
        .filter(AdminSession.token_id == jti, AdminSession.revoked == False)  # noqa: E712
        .first()
    )
    if not session or session.expires_at < dt.datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée.")

    admin = db.query(Admin).filter(Admin.id == admin_id).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte admin introuvable ou désactivé.")

    return admin
