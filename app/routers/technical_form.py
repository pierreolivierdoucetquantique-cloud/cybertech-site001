"""Router : questionnaire technique (après commande)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_client
from app.models.client import Client
from app.models.order import Order, ProductType
from app.models.technical_form import TechnicalForm
from app.schemas.technical_form_schemas import TechnicalFormCreate, TechnicalFormOut
from app.services.email_service import send_technical_form_email
from app.services.audit import log_action

router = APIRouter(prefix="/api/orders/{order_id}/technical-form", tags=["technical-form"])


def _get_owned_order(order_id: str, client: Client, db: Session) -> Order:
    order = db.query(Order).filter(Order.id == order_id, Order.client_id == client.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    return order


@router.get("", response_model=TechnicalFormOut)
def get_technical_form(
    order_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    order = _get_owned_order(order_id, client, db)
    if not order.technical_form:
        raise HTTPException(status_code=404, detail="Aucun questionnaire soumis pour cette commande.")
    return order.technical_form


@router.post("", response_model=TechnicalFormOut, status_code=201)
def submit_technical_form(
    order_id: str,
    payload: TechnicalFormCreate,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    order = _get_owned_order(order_id, client, db)

    if order.product_type == ProductType.MAINTENANCE:
        raise HTTPException(
            status_code=400,
            detail="Le questionnaire technique ne s'applique pas aux contrats de maintenance. Veuillez signer le contrat de maintenance.",
        )

    if order.technical_form:
        raise HTTPException(status_code=400, detail="Un questionnaire a déjà été soumis pour cette commande.")

    form = TechnicalForm(
        order_id=order.id,
        client_id=client.id,
        **payload.model_dump(),
    )
    db.add(form)
    db.commit()
    db.refresh(form)

    log_action(db, actor_type="client", actor_id=client.id, action="submit_technical_form", target_type="order", target_id=order.id)

    summary_html = _build_summary_html(form)
    send_technical_form_email(client, order, summary_html)

    return form


def _build_summary_html(form: TechnicalForm) -> str:
    rows = [
        ("Entreprise", form.company_name),
        ("Secteur", form.business_sector),
        ("Objectifs", form.objectives),
        ("Public cible", form.target_audience),
        ("Pages requises", form.pages_required),
        ("Couleurs souhaitées", form.desired_colors),
        ("Hébergement actuel", form.hosting),
        ("Nom de domaine", form.domain_name),
        ("A un hébergement actuellement", _bool_label(form.has_current_hosting)),
        ("Fournisseur d'hébergement", form.hosting_provider),
        ("Accès à l'hébergement", form.hosting_access_details),
        ("Souhaite un nouvel hébergement CTQ", _bool_label(form.wants_new_hosting)),
        ("Possède déjà un nom de domaine", _bool_label(form.has_domain_name)),
        ("Besoin d'aide pour acheter un domaine", _bool_label(form.wants_domain_help)),
        ("Souhaite transférer un site existant", _bool_label(form.wants_website_transfer)),
    ]
    html = "<table style='width:100%;border-collapse:collapse;'>"
    for label, value in rows:
        if value:
            html += f"<tr><td style='padding:4px 8px;color:#666;'>{label}</td><td style='padding:4px 8px;'>{value}</td></tr>"
    html += "</table>"
    return html


def _bool_label(value) -> str:
    if value is True:
        return "Oui"
    if value is False:
        return "Non"
    return ""
