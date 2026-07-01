"""Schémas Pydantic : formulaire de contact public + vue admin."""
import datetime as dt

from pydantic import BaseModel, EmailStr, field_validator


class ContactMessageIn(BaseModel):
    prenom: str
    nom: str
    courriel: EmailStr
    telephone: str | None = None
    sujet: str
    message: str

    @field_validator("prenom", "nom", "sujet", "message")
    @classmethod
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Ce champ est requis.")
        return v.strip()


class ContactMessageOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    subject: str
    message: str
    email_sent: bool
    is_read: bool
    is_archived: bool
    created_at: dt.datetime

    class Config:
        from_attributes = True


class ContactMessageUpdate(BaseModel):
    is_read: bool | None = None
    is_archived: bool | None = None
