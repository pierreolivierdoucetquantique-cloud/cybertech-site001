"""Router : gestion des commandes (paniers) par l'admin (CRM commandes)."""
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.client import Client
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.schemas.order_schemas import OrderAdminUpdate, OrderItemAdminUpdate
from app.services.audit import log_action
from app.services.billing import create_invoice_for_order, sync_invoice_for_order

router = APIRouter(prefix="/api/admin/orders", tags=["admin-orders"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _item_to_dict(item: OrderItem) -> dict:
    from app.services.progress_utils import step_label_for, color_for
    return {
        "id": item.id,
        "product_type": item.product_type,
        "product_name": item.product_name,
        "price": item.price,
        "project_progress": item.project_progress,
        "progress_step_label": step_label_for(item.project_progress),
        "progress_color": color_for(item.project_progress),
        "expected_delivery_date": item.expected_delivery_date,
        "has_technical_form": item.technical_form is not None,
        "has_maintenance_contract": item.maintenance_contract is not None,
    }


def _order_to_dict(order: Order, client: Client) -> dict:
    invoice = order.invoice
    return {
        "id": order.id,
        "order_number": order.order_number,
        "client_id": client.id,
        "client_name": f"{client.first_name} {client.last_name}",
        "client_email": client.email,
        "items": [_item_to_dict(i) for i in order.items],
        "subtotal": order.subtotal,
        "gst_amount": order.gst_amount,
        "qst_amount": order.qst_amount,
        "total": order.total,
        "taxes_applied": order.taxes_applied == "true",
        "status": order.status,
        "payment_status": order.payment_status,
        "notes": order.notes,
        "has_invoice": invoice is not None,
        "invoice_number": invoice.invoice_number if invoice else None,
        "invoice_status": invoice.status if invoice else None,
        "deposit_amount": invoice.deposit_amount if invoice else None,
        "amount_paid": invoice.amount_paid if invoice else 0.0,
        "remaining_balance": invoice.remaining_balance if invoice else order.total,
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

    # Crée ou met à jour automatiquement la facture dès que le statut de
    # paiement change vers un état "payé" (dépôt, complet, remboursé) — couvre
    # aussi bien la première confirmation que les changements manuels
    # ultérieurs faits par l'admin (ex : solde marqué payé manuellement).
    payment_relevant_states = (
        PaymentStatus.DEPOSIT_PAID, PaymentStatus.PAID,
        PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED,
    )
    if order.payment_status in payment_relevant_states and order.payment_status != previous_payment_status:
        sync_invoice_for_order(db, order, order.client)
        db.refresh(order)

    return _order_to_dict(order, order.client)


@router.put("/{order_id}/items/{item_id}")
def update_order_item(
    order_id: str,
    item_id: str,
    payload: OrderItemAdminUpdate,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Met à jour la progression / date de livraison d'UN service précis du panier."""
    item = db.query(OrderItem).filter(OrderItem.id == item_id, OrderItem.order_id == order_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Service introuvable dans cette commande.")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(item, field, value)
    item.updated_at = dt.datetime.utcnow()
    db.commit()
    db.refresh(item)

    log_action(
        db, actor_type="admin", actor_id=admin.id, action="update_order_item",
        target_type="order_item", target_id=item.id, details=str(updates),
        ip_address=_client_ip(request),
    )

    return _item_to_dict(item)


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
