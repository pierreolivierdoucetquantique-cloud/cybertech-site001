"""Schémas Pydantic : contrat de maintenance électronique."""
import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field

from app.models.maintenance_contract import ContractStatus


class MaintenanceContractInfoIn(BaseModel):
    """
    Informations confirmées/complétées par le client avant signature.
    Le nom/courriel sont pré-remplis depuis le profil client mais modifiables
    ici (ex: nom de l'entreprise différent du nom du titulaire du compte).
    """
    client_full_name: str
    company_name: Optional[str] = None
    client_email: str
    client_phone: Optional[str] = None
    website_concerned: Optional[str] = None


class MaintenanceContractSignIn(BaseModel):
    signer_name: str = Field(..., min_length=2)
    client_signature_data: str = Field(..., min_length=10)  # data URL (dessinée) ou nom tapé
    signature_type: str = Field(..., pattern="^(drawn|typed)$")
    accepted_terms: bool

    class Config:
        pass


class MaintenanceContractOut(BaseModel):
    id: str
    contract_number: str
    order_id: str
    status: ContractStatus

    client_full_name: str
    company_name: Optional[str] = None
    client_email: str
    client_phone: Optional[str] = None
    website_concerned: Optional[str] = None

    maintenance_plan: str
    annual_price: float
    contract_duration_months: int
    effective_date: dt.date
    expiration_date: dt.date

    signer_name: Optional[str] = None
    signature_type: Optional[str] = None
    accepted_terms: bool
    signed_at: Optional[dt.datetime] = None

    pdf_path: Optional[str] = None

    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        from_attributes = True


class MaintenanceContractAdminOut(MaintenanceContractOut):
    client_id: str
    client_signature_data: Optional[str] = None
    signed_ip_address: Optional[str] = None
    admin_signature_name: Optional[str] = None
    admin_signed_at: Optional[dt.datetime] = None
