"""Modèle de données : Client."""
import uuid
import datetime as dt

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Client(Base):
    __tablename__ = "clients"

    id = Column(String, primary_key=True, default=gen_uuid)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)

    # Adresse
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    country = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)  # False = compte désactivé par admin
    email_verified = Column(Boolean, default=False)

    password_reset_token = Column(String, nullable=True, index=True)
    password_reset_expires = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    # Relations
    orders = relationship("Order", back_populates="client", cascade="all, delete-orphan")
    technical_forms = relationship("TechnicalForm", back_populates="client", cascade="all, delete-orphan")
    sessions = relationship("ClientSession", back_populates="client", cascade="all, delete-orphan")


class ClientSession(Base):
    """Sessions actives, pour pouvoir les révoquer (ex: lors d'un changement de mot de passe)."""
    __tablename__ = "client_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False)
    token_id = Column(String, unique=True, nullable=False, index=True)  # jti du JWT
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)

    client = relationship("Client", back_populates="sessions")
