"""Router : gestion des paiements par l'admin (validation Interac)."""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.order import PaymentStatus
from app.models.payment import Payment, PaymentRequestStatus, PaymentAmountType, PaymentMethod
from app.schemas.payment_schemas import PaymentAdminOut, PaymentReviewDecision
from app.services.audit import log_action
from app.services.billing import create_invoice_for_order

router = APIRouter(prefix="/api/admin/payments", tags=["admin-payments"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _to_admin_out(p: Payment) -> PaymentAdminOut:
    out = PaymentAdminOut.model_validate(p)
    out.client_name = f"{p.client.first_name} {p.client.last_name}" if p.client else None
    out.client_email = p.client.email if p.client else None
    out.order_number = p.order.order_number if p.order else None
    return out


@router.get("", response_model=list[PaymentAdminOut])
def list_payments(
    pending_only: bool = False,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Payment).filter(Payment.method == PaymentMethod.INTERAC)
    if pending_only:
        query = query.filter(Payment.status == PaymentRequestStatus.PENDING_VALIDATION)
    payments = query.order_by(Payment.created_at.desc()).all()
    return [_to_admin_out(p) for p in payments]


@router.post("/{payment_id}/review", response_model=PaymentAdminOut)
def review_payment(
    payment_id: str,
    payload: PaymentReviewDecision,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")
    if payment.status != PaymentRequestStatus.PENDING_VALIDATION:
        raise HTTPException(status_code=400, detail="Ce paiement n'est pas en attente de validation.")

    payment.reviewed_by_admin_id = admin.id
    payment.reviewed_at = dt.datetime.utcnow()
    payment.admin_review_note = payload.note

    if payload.approve:
        payment.status = PaymentRequestStatus.APPROVED
        order = payment.order
        if payment.amount_type == PaymentAmountType.FULL:
            order.payment_status = PaymentStatus.PAID
        else:
            order.payment_status = PaymentStatus.DEPOSIT_PAID
        db.commit()
        db.refresh(order)
        if not order.invoice:
            create_invoice_for_order(db, order, payment.client)
        log_action(db, actor_type="admin", actor_id=admin.id, action="approve_payment", target_type="payment", target_id=payment.id, ip_address=_client_ip(request))
    else:
        payment.status = PaymentRequestStatus.REJECTED
        db.commit()
        log_action(db, actor_type="admin", actor_id=admin.id, action="reject_payment", target_type="payment", target_id=payment.id, details=payload.note, ip_address=_client_ip(request))

    db.refresh(payment)
    return _to_admin_out(payment)
