"""
Router : formulaire de contact public (page d'accueil / page contact).

Chaque message est TOUJOURS persisté en base de données, même si l'envoi
par courriel échoue (clé Resend absente, panne du service, etc.). Cela
garantit qu'aucun message client n'est jamais perdu silencieusement —
l'admin peut toujours le consulter dans le panneau d'administration.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.contact_schemas import ContactMessageIn
from app.models.contact_message import ContactMessage
from app.services.email_service import send_contact_form_email
from app.services.audit import log_action

router = APIRouter(prefix="/api/contact", tags=["contact"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("")
def send_contact_message(payload: ContactMessageIn, request: Request, db: Session = Depends(get_db)):
    sent = send_contact_form_email(
        payload.prenom, payload.nom, payload.courriel,
        payload.telephone, payload.sujet, payload.message,
    )

    record = ContactMessage(
        first_name=payload.prenom,
        last_name=payload.nom,
        email=payload.courriel,
        phone=payload.telephone,
        subject=payload.sujet,
        message=payload.message,
        email_sent=sent,
    )
    db.add(record)
    db.commit()

    log_action(
        db, actor_type="client", action="contact_message_received",
        target_type="contact_message", target_id=record.id,
        details=f"{payload.prenom} {payload.nom} <{payload.courriel}> — email_sent={sent}",
        ip_address=_client_ip(request),
    )

    # On ne fait jamais échouer la requête côté utilisateur même si l'email
    # échoue côté serveur — le message est dans tous les cas enregistré et
    # consultable par l'admin dans le panneau d'administration.
    return {"message": "Votre message a été envoyé avec succès.", "email_sent": sent}
