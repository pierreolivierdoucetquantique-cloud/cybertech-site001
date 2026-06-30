"""Schémas Pydantic : authentification et gestion admin."""
import datetime as dt
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.schemas.client_schemas import validate_password_strength


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class AdminOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str
    created_at: dt.datetime
    last_login_at: Optional[dt.datetime] = None

    class Config:
        from_attributes = True


class AdminPasswordResetRequest(BaseModel):
    email: EmailStr


class AdminPasswordResetConfirm(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v):
        return validate_password_strength(v)


class ClientAdminOut(BaseModel):
    """Vue client pour l'admin (inclut plus d'infos que ClientOut public)."""
    id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    is_active: bool
    created_at: dt.datetime
    order_count: int = 0

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_clients: int
    total_orders: int
    total_invoices: int
    total_revenue: float
    pending_orders: int
    processing_orders: int
    delivered_orders: int
    active_maintenance_contracts: int
    recent_registrations: int  # derniers 30 jours
