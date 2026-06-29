"""Router : questionnaire technique (après commande), un par OrderItem (v9.11)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_client
from app.models.client import Client
from app.models.order import OrderItem, Order, ProductType
from app.models.technical_form import TechnicalForm
from app.schemas.technical_form_schemas import TechnicalFormCreate, TechnicalFormOut
from app.services.email_service import send_technical_form_email
from app.services.audit import log_action

router = APIRouter(prefix="/api/order-items/{order_item_id}/technical-form", tags=["technical-form"])


def _get_owned_item(order_item_id: str, client: Client, db: Session) -> OrderItem:
    item = (
        db.query(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(OrderItem.id == order_item_id, Order.client_id == client.id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Service introuvable dans votre commande.")
    return item


@router.get("", response_model=TechnicalFormOut)
def get_technical_form(
    order_item_id: str,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(order_item_id, client, db)
    if not item.technical_form:
        raise HTTPException(status_code=404, detail="Aucun questionnaire soumis pour ce service.")
    return item.technical_form


@router.post("", response_model=TechnicalFormOut, status_code=201)
def submit_technical_form(
    order_item_id: str,
    payload: TechnicalFormCreate,
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db),
):
    item = _get_owned_item(order_item_id, client, db)

    if item.product_type == ProductType.MAINTENANCE:
        raise HTTPException(
            status_code=400,
            detail="Le questionnaire technique ne s'applique pas aux contrats de maintenance. Veuillez signer le contrat de maintenance.",
        )

    if item.technical_form:
        raise HTTPException(status_code=400, detail="Un questionnaire a déjà été soumis pour ce service.")

    form = TechnicalForm(
        order_item_id=item.id,
        client_id=client.id,
        **payload.model_dump(),
    )
    db.add(form)
    db.commit()
    db.refresh(form)

    log_action(db, actor_type="client", actor_id=client.id, action="submit_technical_form", target_type="order_item", target_id=item.id)

    summary_html = _build_summary_html(form)
    send_technical_form_email(client, item, summary_html)

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
