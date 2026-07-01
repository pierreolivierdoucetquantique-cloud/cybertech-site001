"""Router : consultation des questionnaires techniques par l'admin (un par OrderItem, v9.11)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.client import Client
from app.models.order import Order, OrderItem
from app.models.technical_form import TechnicalForm

router = APIRouter(prefix="/api/admin/technical-forms", tags=["admin-technical-forms"])


def _form_to_dict(form: TechnicalForm, item: Optional[OrderItem], order: Optional[Order], client: Optional[Client]) -> dict:
    return {
        "id": form.id,
        "order_item_id": form.order_item_id,
        "order_number": order.order_number if order else None,
        "product_name": item.product_name if item else None,
        "client_id": form.client_id,
        "client_name": f"{client.first_name} {client.last_name}" if client else "—",
        "client_email": client.email if client else "—",
        "company_name": form.company_name,
        "business_sector": form.business_sector,
        "description": form.description,
        "objectives": form.objectives,
        "target_audience": form.target_audience,
        "pages_required": form.pages_required,
        "desired_colors": form.desired_colors,
        "has_existing_logo": form.has_existing_logo,
        "has_images": form.has_images,
        "feature_booking": form.feature_booking,
        "feature_payment": form.feature_payment,
        "feature_blog": form.feature_blog,
        "feature_gallery": form.feature_gallery,
        "feature_shop": form.feature_shop,
        "languages": form.languages,
        "hosting": form.hosting,
        "domain_name": form.domain_name,
        "reference_websites": form.reference_websites,
        "additional_notes": form.additional_notes,
        "has_current_hosting": form.has_current_hosting,
        "hosting_provider": form.hosting_provider,
        "hosting_access_details": form.hosting_access_details,
        "wants_new_hosting": form.wants_new_hosting,
        "has_domain_name": form.has_domain_name,
        "wants_domain_help": form.wants_domain_help,
        "wants_website_transfer": form.wants_website_transfer,
        "submitted_at": form.submitted_at,
    }


@router.get("")
def list_technical_forms(
    search: Optional[str] = None,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    forms = db.query(TechnicalForm).order_by(TechnicalForm.submitted_at.desc()).all()

    results = []
    for form in forms:
        item = db.query(OrderItem).filter(OrderItem.id == form.order_item_id).first()
        order = db.query(Order).filter(Order.id == item.order_id).first() if item else None
        client = db.query(Client).filter(Client.id == form.client_id).first()
        results.append((form, item, order, client))

    if search:
        s = search.strip().lower()
        results = [
            (f, it, o, c) for f, it, o, c in results
            if (f.company_name and s in f.company_name.lower())
            or (c and (s in c.first_name.lower() or s in c.last_name.lower() or s in c.email.lower()))
            or (o and s in o.order_number.lower())
        ]

    return [_form_to_dict(f, it, o, c) for f, it, o, c in results]


@router.get("/{form_id}")
def get_technical_form_detail(
    form_id: str,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    form = db.query(TechnicalForm).filter(TechnicalForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Questionnaire introuvable.")
    item = db.query(OrderItem).filter(OrderItem.id == form.order_item_id).first()
    order = db.query(Order).filter(Order.id == item.order_id).first() if item else None
    client = db.query(Client).filter(Client.id == form.client_id).first()
    return _form_to_dict(form, item, order, client)
