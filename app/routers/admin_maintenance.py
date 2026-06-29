"""
Router : gestion des contrats de maintenance par l'admin.

Un contrat de maintenance est une Order avec product_type == MAINTENANCE.
Cette vue dédiée calcule en plus la date de renouvellement (1 an après le
paiement confirmé) et signale les contrats à renouveler bientôt ou expirés,
ce qui n'est pas visible dans la vue générique "Commandes". Elle expose
aussi l'état du Contrat de Maintenance électronique (signature, PDF) lié à
chaque commande, lorsqu'il existe.
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
from app.models.order import Order, ProductType, PaymentStatus, OrderStatus
from app.models.maintenance_contract import MaintenanceContract, ContractStatus
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin/maintenance", tags=["admin-maintenance"])

RENEWAL_PERIOD_DAYS = 365
RENEWAL_WARNING_DAYS = 30  # signale comme "à renouveler bientôt" sous ce seuil


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _renewal_state(contract: Order) -> dict:
    """Calcule la date de renouvellement et l'état (actif/à renouveler/expiré)."""
    is_active_payment = contract.payment_status in (PaymentStatus.DEPOSIT_PAID, PaymentStatus.PAID)
    is_cancelled = contract.status == OrderStatus.CANCELLED

    renewal_date = contract.created_at + dt.timedelta(days=RENEWAL_PERIOD_DAYS)
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


def _contract_to_dict(contract: Order, client: Client) -> dict:
    renewal = _renewal_state(contract)
    mc: Optional[MaintenanceContract] = contract.maintenance_contract
    return {
        "id": contract.id,
        "order_number": contract.order_number,
        "client_id": client.id,
        "client_name": f"{client.first_name} {client.last_name}",
        "client_email": client.email,
        "price": contract.price,
        "status": contract.status,
        "payment_status": contract.payment_status,
        "started_at": contract.created_at,
        "renewal_date": renewal["renewal_date"],
        "days_remaining": renewal["days_remaining"],
        "renewal_state": renewal["state"],
        "notes": contract.notes,
        "contract_id": mc.id if mc else None,
        "contract_number": mc.contract_number if mc else None,
        "contract_status": mc.status if mc else None,
        "contract_signed_at": mc.signed_at if mc else None,
        "contract_has_pdf": bool(mc and mc.pdf_path and os.path.exists(mc.pdf_path)),
    }


@router.get("")
def list_maintenance_contracts(
    state_filter: Optional[str] = None,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    contracts = (
        db.query(Order)
        .filter(Order.product_type == ProductType.MAINTENANCE)
        .order_by(Order.created_at.desc())
        .all()
    )
    results = [_contract_to_dict(c, c.client) for c in contracts]

    if state_filter:
        results = [r for r in results if r["renewal_state"] == state_filter]

    return results


@router.get("/summary")
def maintenance_summary(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Compte rapide par état, pour affichage en cartes au-dessus du tableau."""
    contracts = (
        db.query(Order)
        .filter(Order.product_type == ProductType.MAINTENANCE)
        .all()
    )
    counts = {"active": 0, "renewal_soon": 0, "expired": 0, "unpaid": 0, "cancelled": 0}
    for c in contracts:
        state = _renewal_state(c)["state"]
        counts[state] = counts.get(state, 0) + 1
    counts["total"] = len(contracts)
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


@router.put("/{contract_id}/notes")
def update_maintenance_notes(
    contract_id: str,
    payload: dict,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    contract = (
        db.query(Order)
        .filter(Order.id == contract_id, Order.product_type == ProductType.MAINTENANCE)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Contrat de maintenance introuvable.")

    contract.notes = payload.get("notes", contract.notes)
    contract.updated_at = dt.datetime.utcnow()
    db.commit()
    db.refresh(contract)

    log_action(
        db, actor_type="admin", actor_id=admin.id, action="update_maintenance_notes",
        target_type="order", target_id=contract.id, ip_address=_client_ip(request),
    )

    return _contract_to_dict(contract, contract.client)
