"""Modèle de données : Admin (administrateur) et AuditLog (journal d'audit)."""
import datetime as dt

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text

from app.database import Base
from app.models.client import gen_uuid


class Admin(Base):
    __tablename__ = "admins"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)
    role = Column(String, default="admin")  # extensible pour rôles futurs

    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)  # verrouillage temporaire (rate limiting)

    password_reset_token = Column(String, nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)


class AdminSession(Base):
    """Sessions admin actives — durée de vie courte, révocables."""
    __tablename__ = "admin_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    admin_id = Column(String, nullable=False)
    token_id = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)


class AuditLog(Base):
    """Journal d'audit : trace toutes les actions sensibles (admin et client)."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    actor_type = Column(String, nullable=False)  # "admin" | "client" | "system"
    actor_id = Column(String, nullable=True)
    action = Column(String, nullable=False)  # ex: "login", "delete_account", "update_order"
    target_type = Column(String, nullable=True)  # ex: "order", "client"
    target_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
