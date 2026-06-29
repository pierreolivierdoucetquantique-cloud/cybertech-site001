"""Schémas Pydantic : questionnaire technique."""
import datetime as dt
from typing import Optional

from pydantic import BaseModel


class TechnicalFormCreate(BaseModel):
    company_name: Optional[str] = None
    business_sector: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[str] = None
    target_audience: Optional[str] = None
    pages_required: Optional[str] = None
    desired_colors: Optional[str] = None
    has_existing_logo: bool = False
    has_images: bool = False

    feature_booking: bool = False
    feature_payment: bool = False
    feature_blog: bool = False
    feature_gallery: bool = False
    feature_shop: bool = False
    languages: Optional[str] = None

    hosting: Optional[str] = None
    domain_name: Optional[str] = None
    reference_websites: Optional[str] = None
    additional_notes: Optional[str] = None

    # --- Section Hébergement Web ---
    has_current_hosting: Optional[bool] = None
    hosting_provider: Optional[str] = None
    hosting_access_details: Optional[str] = None
    wants_new_hosting: Optional[bool] = None
    has_domain_name: Optional[bool] = None
    wants_domain_help: Optional[bool] = None
    wants_website_transfer: Optional[bool] = None


class TechnicalFormOut(TechnicalFormCreate):
    id: str
    order_id: str
    submitted_at: dt.datetime

    class Config:
        from_attributes = True
