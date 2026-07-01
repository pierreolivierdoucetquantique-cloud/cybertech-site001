"""Router : profil client (consulter, modifier, changer mot de passe, supprimer)."""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.dependencies import get_current_client
from app.models.client import Client, ClientSession
from app.schemas.client_schemas import (
    ClientOut, ClientProfileUpdate, ClientPasswordChange, ClientAccountDelete,
)
from app.utils.security import verify_password, hash_password
from app.services.audit import log_action

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/me", response_model=ClientOut)
def get_me(client: Client = Depends(get_current_client)):
    return client


@router.put("/me", response_model=ClientOut)
def update_me(
    payload: ClientProfileUpdate,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    client.updated_at = dt.datetime.utcnow()
    db.commit()
    db.refresh(client)
    return client


@router.post("/change-password")
def change_password(
    payload: ClientPasswordChange,
    request: Request,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, client.password_hash):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect.")

    client.password_hash = hash_password(payload.new_password)
    client.updated_at = dt.datetime.utcnow()

    # Révoque toutes les autres sessions actives par sécurité
    db.query(ClientSession).filter(ClientSession.client_id == client.id).update({"revoked": True})
    db.commit()

    log_action(db, actor_type="client", actor_id=client.id, action="change_password", ip_address=_client_ip(request))
    return {"message": "Mot de passe modifié. Veuillez vous reconnecter."}


@router.get("/me/documents")
def list_my_documents(
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    """Documents téléversés par l'admin et destinés à ce client."""
    from app.models.upload import UploadedFile
    docs = (
        db.query(UploadedFile)
        .filter(UploadedFile.related_client_id == client.id, UploadedFile.category == "client_document")
        .order_by(UploadedFile.created_at.desc())
        .all()
    )
    return [
        {"file_id": d.id, "url": f"/api/files/{d.id}", "filename": d.original_filename, "created_at": d.created_at}
        for d in docs
    ]


@router.delete("/me")
def delete_account(
    payload: ClientAccountDelete,
    request: Request,
    response: Response,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.password, client.password_hash):
        raise HTTPException(status_code=400, detail="Mot de passe incorrect.")

    client_id = client.id
    client_email = client.email

    log_action(
        db, actor_type="client", actor_id=client_id, action="delete_account",
        details=client_email, ip_address=_client_ip(request),
    )

    # La suppression du client entraîne, via cascade="all, delete-orphan" sur
    # les relations du modèle, la suppression des commandes, factures liées
    # aux commandes, formulaires techniques, et sessions.
    db.delete(client)
    db.commit()

    response.delete_cookie(settings.COOKIE_NAME, path="/")
    return {"message": "Votre compte et toutes les données associées ont été supprimés définitivement."}
