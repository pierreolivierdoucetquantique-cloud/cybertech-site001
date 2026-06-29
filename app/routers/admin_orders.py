"""Router : gestion des commandes par l'admin (CRM commandes)."""
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.client import Client
from app.models.order import Order, OrderStatus, PaymentStatus
from app.schemas.order_schemas import OrderAdminUpdate
from app.services.audit import log_action
from app.services.billing import create_invoice_for_order

router = APIRouter(prefix="/api/admin/orders", tags=["admin-orders"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _order_to_dict(order: Order, client: Client) -> dict:
    from app.services.progress_utils import step_label_for, color_for
    return {
        "id": order.id,
        "order_number": order.order_number,
        "client_id": client.id,
        "client_name": f"{client.first_name} {client.last_name}",
        "client_email": client.email,
        "product_type": order.product_type,
        "product_name": order.product_name,
        "price": order.price,
        "status": order.status,
        "payment_status": order.payment_status,
        "project_progress": order.project_progress,
        "progress_step_label": step_label_for(order.project_progress),
        "progress_color": color_for(order.project_progress),
        "expected_delivery_date": order.expected_delivery_date,
        "notes": order.notes,
        "has_invoice": order.invoice is not None,
        "invoice_number": order.invoice.invoice_number if order.invoice else None,
        "has_technical_form": order.technical_form is not None,
        "updated_at": order.updated_at,
        "created_at": order.created_at,
    }


@router.get("")
def list_orders(
    status_filter: Optional[OrderStatus] = Query(None, alias="status"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Order)
    if status_filter:
        query = query.filter(Order.status == status_filter)
    orders = query.order_by(Order.created_at.desc()).all()
    return [_order_to_dict(o, o.client) for o in orders]


@router.get("/unpaid-followups")
def list_unpaid_followups(
    min_days: int = 3,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Commandes non payées depuis au moins `min_days` jours, non annulées —
    pour savoir rapidement quels clients relancer.
    """
    threshold = dt.datetime.utcnow() - dt.timedelta(days=min_days)
    orders = (
        db.query(Order)
        .filter(
            Order.payment_status == PaymentStatus.UNPAID,
            Order.status != OrderStatus.CANCELLED,
            Order.created_at <= threshold,
        )
        .order_by(Order.created_at.asc())
        .all()
    )
    results = []
    for o in orders:
        days_unpaid = (dt.datetime.utcnow() - o.created_at).days
        results.append(_order_to_dict(o, o.client) | {"days_unpaid": days_unpaid})
    return results


@router.get("/{order_id}")
def get_order(order_id: str, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable.")
    return _order_to_dict(order, order.client)


@router.put("/{order_id}")
def update_order(
    order_id: str,
    payload: OrderAdminUpdate,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable.")

    previous_payment_status = order.payment_status

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(order, field, value)
    order.updated_at = dt.datetime.utcnow()
    db.commit()
    db.refresh(order)

    log_action(
        db, actor_type="admin", actor_id=admin.id, action="update_order",
        target_type="order", target_id=order.id, details=str(updates),
        ip_address=_client_ip(request),
    )

    # Génère automatiquement la facture dès qu'un paiement (dépôt ou complet)
    # est confirmé pour la première fois, si elle n'existe pas déjà.
    payment_confirmed = order.payment_status in (PaymentStatus.DEPOSIT_PAID, PaymentStatus.PAID)
    if payment_confirmed and previous_payment_status == PaymentStatus.UNPAID and not order.invoice:
        create_invoice_for_order(db, order, order.client)
        db.refresh(order)

    return _order_to_dict(order, order.client)


@router.post("/{order_id}/generate-invoice")
def manually_generate_invoice(
    order_id: str,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Permet à l'admin de forcer la génération de facture si besoin (idempotent)."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Commande introuvable.")

    invoice = create_invoice_for_order(db, order, order.client)
    log_action(db, actor_type="admin", actor_id=admin.id, action="manual_generate_invoice", target_type="invoice", target_id=invoice.id, ip_address=_client_ip(request))
    return {"message": f"Facture {invoice.invoice_number} générée.", "invoice_number": invoice.invoice_number}
