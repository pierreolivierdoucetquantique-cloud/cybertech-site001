"""Schémas Pydantic : validation des entrées/sorties pour les clients."""
import re
import datetime as dt
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
    if not re.search(r"[A-Za-z]", password):
        raise ValueError("Le mot de passe doit contenir au moins une lettre.")
    if not re.search(r"[0-9]", password):
        raise ValueError("Le mot de passe doit contenir au moins un chiffre.")
    return password


class ClientRegister(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, v):
        return validate_password_strength(v)

    @field_validator("first_name", "last_name")
    @classmethod
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Ce champ est requis.")
        return v.strip()


class ClientLogin(BaseModel):
    email: EmailStr
    password: str


class ClientProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


class ClientPasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v):
        return validate_password_strength(v)


class ClientAccountDelete(BaseModel):
    password: str
    confirmation: str  # doit être exactement "SUPPRIMER"

    @field_validator("confirmation")
    @classmethod
    def check_confirmation(cls, v):
        if v != "SUPPRIMER":
            raise ValueError('Veuillez taper exactement "SUPPRIMER" pour confirmer.')
        return v


class ClientOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    created_at: dt.datetime

    class Config:
        from_attributes = True
