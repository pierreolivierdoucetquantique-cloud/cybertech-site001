"""Router : mot de passe oublié (demande client + confirmation via token)."""
import datetime as dt
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client, ClientSession
from app.schemas.client_schemas import validate_password_strength
from app.services.email_service import send_password_reset_email
from app.services.audit import log_action
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v):
        return validate_password_strength(v)


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.email == payload.email.lower()).first()

    # Réponse identique que le client existe ou non, pour ne pas révéler
    # quelles adresses sont enregistrées (énumération d'utilisateurs).
    generic_message = {"message": "Si un compte existe avec ce courriel, un lien de réinitialisation a été envoyé."}

    if not client:
        return generic_message

    token = secrets.token_urlsafe(32)
    client.password_reset_token = token
    client.password_reset_expires = dt.datetime.utcnow() + dt.timedelta(hours=1)
    db.commit()

    reset_link = f"{settings.FRONTEND_URL}/reset-password.html?token={token}"
    send_password_reset_email(client.email, reset_link, client.first_name)
    log_action(db, actor_type="client", actor_id=client.id, action="forgot_password_request")

    return generic_message


@router.post("/reset-password")
def reset_password(payload: ResetPasswordConfirm, db: Session = Depends(get_db)):
    from app.utils.security import hash_password

    client = db.query(Client).filter(Client.password_reset_token == payload.token).first()
    if not client or not client.password_reset_expires or client.password_reset_expires < dt.datetime.utcnow():
        raise HTTPException(status_code=400, detail="Ce lien de réinitialisation est invalide ou expiré.")

    client.password_hash = hash_password(payload.new_password)
    client.password_reset_token = None
    client.password_reset_expires = None

    # Révoque toutes les sessions actives par sécurité
    db.query(ClientSession).filter(ClientSession.client_id == client.id).update({"revoked": True})
    db.commit()

    log_action(db, actor_type="client", actor_id=client.id, action="reset_password_success")

    return {"message": "Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter."}
