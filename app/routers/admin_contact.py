"""Router : consultation et gestion des messages de contact reçus (admin)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.contact_message import ContactMessage
from app.schemas.contact_schemas import ContactMessageOut, ContactMessageUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin/contact-messages", tags=["admin-contact"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("", response_model=list[ContactMessageOut])
def list_contact_messages(
    is_read: Optional[bool] = Query(None),
    is_archived: Optional[bool] = Query(False, description="Par défaut, n'affiche pas les messages archivés"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(ContactMessage)
    if is_read is not None:
        query = query.filter(ContactMessage.is_read == is_read)
    if is_archived is not None:
        query = query.filter(ContactMessage.is_archived == is_archived)
    return query.order_by(ContactMessage.created_at.desc()).all()


@router.get("/unread-count")
def unread_count(admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    count = (
        db.query(func.count(ContactMessage.id))
        .filter(ContactMessage.is_read == False, ContactMessage.is_archived == False)  # noqa: E712
        .scalar() or 0
    )
    return {"unread_count": count}


@router.get("/{message_id}", response_model=ContactMessageOut)
def get_contact_message(message_id: str, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    msg = db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message introuvable.")
    return msg


@router.put("/{message_id}", response_model=ContactMessageOut)
def update_contact_message(
    message_id: str,
    payload: ContactMessageUpdate,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    msg = db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message introuvable.")

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(msg, field, value)
    db.commit()

    log_action(
        db, actor_type="admin", actor_id=admin.id, action="update_contact_message",
        target_type="contact_message", target_id=msg.id, details=str(data),
        ip_address=_client_ip(request),
    )
    return msg


@router.delete("/{message_id}")
def delete_contact_message(message_id: str, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    msg = db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message introuvable.")
    log_action(
        db, actor_type="admin", actor_id=admin.id, action="delete_contact_message",
        target_type="contact_message", target_id=message_id,
        details=f"{msg.first_name} {msg.last_name} <{msg.email}>",
        ip_address=_client_ip(request),
    )
    db.delete(msg)
    db.commit()
    return {"message": "Message supprimé."}
