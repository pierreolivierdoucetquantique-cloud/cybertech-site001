"""
Modèle de données : message de contact (formulaire public).

Persisté en base en plus de l'envoi par email, pour qu'aucun message ne soit
jamais perdu même si l'envoi email échoue (clé Resend absente, panne, etc.).
L'admin peut consulter, marquer comme lu/traité et archiver ces messages
depuis le panneau d'administration.
"""
import datetime as dt

from sqlalchemy import Column, String, Text, DateTime, Boolean

from app.database import Base
from app.models.client import gen_uuid


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(String, primary_key=True, default=gen_uuid)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    email_sent = Column(Boolean, default=False)  # l'envoi par courriel a-t-il réussi ?
    is_read = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)

    created_at = Column(DateTime, default=dt.datetime.utcnow, index=True)
