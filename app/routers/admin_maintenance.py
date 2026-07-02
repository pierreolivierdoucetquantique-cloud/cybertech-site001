"""
Router : gestion des contrats de maintenance par l'admin.

v9.11 : un "contrat de maintenance" est désormais un OrderItem avec
product_type == MAINTENANCE (auparavant, c'était l'Order entière — avant le
panier multi-services, une commande ne contenait qu'un seul service).
Cette vue dédiée calcule en plus la date de renouvellement (1 an après le
paiement confirmé du panier) et signale les contrats à renouveler bientôt ou
expirés, ce qui n'est pas visible dans la vue générique "Commandes". Elle
expose aussi l'état du Contrat de Maintenance électronique (signature, PDF)
lié à chaque item, lorsqu'il existe.
"""
import os
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.client import Client
from app.models.order import Order, OrderItem, ProductType, PaymentStatus, OrderStatus
from app.models.maintenance_contract import MaintenanceContract, ContractStatus
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin/maintenance", tags=["admin-maintenance"])

RENEWAL_PERIOD_DAYS = 365
RENEWAL_WARNING_DAYS = 30  # signale comme "à renouveler bientôt" sous ce seuil


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _renewal_state(item: OrderItem, order: Order) -> dict:
    """Calcule la date de renouvellement et l'état (actif/à renouveler/expiré)."""
    mc: Optional[MaintenanceContract] = item.maintenance_contract

    # Priorité à la date d'expiration réelle du contrat signé, si disponible ;
    # sinon, estimation à partir de la date de paiement du panier (fallback).
    if mc and mc.expiration_date:
        renewal_date = dt.datetime.combine(mc.expiration_date, dt.time.min)
    else:
        renewal_date = order.created_at + dt.timedelta(days=RENEWAL_PERIOD_DAYS)

    is_active_payment = order.payment_status in (PaymentStatus.DEPOSIT_PAID, PaymentStatus.PAID)
    is_cancelled = order.status == OrderStatus.CANCELLED

    days_remaining = (renewal_date - dt.datetime.utcnow()).days

    if is_cancelled:
        state = "cancelled"
    elif not is_active_payment:
        state = "unpaid"
    elif days_remaining < 0:
        state = "expired"
    elif days_remaining <= RENEWAL_WARNING_DAYS:
        state = "renewal_soon"
    else:
        state = "active"

    return {"renewal_date": renewal_date, "days_remaining": days_remaining, "state": state}


def _contract_to_dict(item: OrderItem, order: Order, client: Client) -> dict:
    renewal = _renewal_state(item, order)
    mc: Optional[MaintenanceContract] = item.maintenance_contract
    return {
        "id": item.id,
        "order_id": order.id,
        "order_number": order.order_number,
        "client_id": client.id,
        "client_name": f"{client.first_name} {client.last_name}",
        "client_email": client.email,
        "price": item.price,
        "status": order.status,
        "payment_status": order.payment_status,
        "started_at": order.created_at,
        "renewal_date": renewal["renewal_date"],
        "days_remaining": renewal["days_remaining"],
        "renewal_state": renewal["state"],
        "notes": order.notes,
        "contract_id": mc.id if mc else None,
        "contract_number": mc.contract_number if mc else None,
        "contract_status": mc.status if mc else None,
        "contract_signed_at": mc.signed_at if mc else None,
        "contract_has_pdf": bool(mc and mc.pdf_path and os.path.exists(mc.pdf_path)),
        "reminder_sent_at": mc.renewal_reminder_sent_at if mc else None,
    }


@router.get("")
def list_maintenance_contracts(
    state_filter: Optional[str] = None,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    items = (
        db.query(OrderItem)
        .filter(OrderItem.product_type == ProductType.MAINTENANCE)
        .order_by(OrderItem.created_at.desc())
        .all()
    )
    results = [_contract_to_dict(i, i.order, i.order.client) for i in items]

    if state_filter:
        results = [r for r in results if r["renewal_state"] == state_filter]

    return results


@router.get("/summary")
def maintenance_summary(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Compte rapide par état, pour affichage en cartes au-dessus du tableau."""
    items = (
        db.query(OrderItem)
        .filter(OrderItem.product_type == ProductType.MAINTENANCE)
        .all()
    )
    counts = {"active": 0, "renewal_soon": 0, "expired": 0, "unpaid": 0, "cancelled": 0}
    for i in items:
        state = _renewal_state(i, i.order)["state"]
        counts[state] = counts.get(state, 0) + 1
    counts["total"] = len(items)
    return counts


@router.get("/contracts/{contract_id}/download")
def download_signed_contract(
    contract_id: str,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    contract = db.query(MaintenanceContract).filter(MaintenanceContract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contrat introuvable.")
    if not contract.pdf_path or not os.path.exists(contract.pdf_path):
        raise HTTPException(status_code=404, detail="Le PDF de ce contrat n'est pas encore disponible (contrat non signé).")

    return FileResponse(
        contract.pdf_path,
        media_type="application/pdf",
        filename=f"{contract.contract_number}.pdf",
    )


@router.put("/{item_id}/notes")
def update_maintenance_notes(
    item_id: str,
    payload: dict,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Les notes restent au niveau du panier (Order), pas de l'item individuel."""
    item = (
        db.query(OrderItem)
        .filter(OrderItem.id == item_id, OrderItem.product_type == ProductType.MAINTENANCE)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Contrat de maintenance introuvable.")

    order = item.order
    order.notes = payload.get("notes", order.notes)
    order.updated_at = dt.datetime.utcnow()
    db.commit()
    db.refresh(order)

    log_action(
        db, actor_type="admin", actor_id=admin.id, action="update_maintenance_notes",
        target_type="order", target_id=order.id, ip_address=_client_ip(request),
    )

    return _contract_to_dict(item, order, order.client)
