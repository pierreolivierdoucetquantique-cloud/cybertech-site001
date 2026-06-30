"""
Router : gestion des paiements par l'admin.

v9.11 — Page Paiements enrichie :
- Affiche TOUTES les transactions (Interac ET Stripe), pas seulement les
  Interac en attente de validation comme avant.
- Colonnes étendues : client, date/heure, services du panier, sous-total,
  TPS, TVQ, total, méthode, marque de carte (si Stripe), statut.
- Recherche (nom/email/numéro de commande), filtre par méthode/statut, tri.
- Remboursement RÉEL via Stripe (pas un changement de statut cosmétique) —
  voir app/services/stripe_service.py:refund_payment. Pour Interac, le
  remboursement reste manuel (hors plateforme) ; l'admin ajuste le statut
  lui-même après avoir effectué le virement de retour.
"""
import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.order import PaymentStatus
from app.models.payment import Payment, PaymentRequestStatus, PaymentAmountType, PaymentMethod
from app.schemas.payment_schemas import PaymentAdminOut, PaymentReviewDecision, PaymentRefundRequest
from app.services.audit import log_action
from app.services.billing import create_invoice_for_order
from app.services.stripe_service import refund_payment as stripe_refund_payment

router = APIRouter(prefix="/api/admin/payments", tags=["admin-payments"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _to_admin_out(p: Payment) -> PaymentAdminOut:
    out = PaymentAdminOut.model_validate(p)
    out.client_name = f"{p.client.first_name} {p.client.last_name}" if p.client else None
    out.client_email = p.client.email if p.client else None
    if p.order:
        out.order_number = p.order.order_number
        out.order_subtotal = p.order.subtotal
        out.order_gst_amount = p.order.gst_amount
        out.order_qst_amount = p.order.qst_amount
        out.order_total = p.order.total
        out.items_summary = ", ".join(item.product_name for item in p.order.items)
    return out


@router.get("", response_model=list[PaymentAdminOut])
def list_payments(
    pending_only: bool = False,
    method: Optional[PaymentMethod] = None,
    status_filter: Optional[PaymentRequestStatus] = Query(None, alias="status"),
    search: Optional[str] = None,
    sort_by: str = Query("created_at", description="created_at | amount | client_name"),
    sort_dir: str = Query("desc", description="asc | desc"),
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Historique COMPLET des transactions (Interac + Stripe), avec recherche,
    filtres et tri. `pending_only` est conservé pour compatibilité avec
    l'ancien widget "validations en attente" du tableau de bord.
    """
    query = db.query(Payment)

    if pending_only:
        query = query.filter(Payment.method == PaymentMethod.INTERAC, Payment.status == PaymentRequestStatus.PENDING_VALIDATION)
    if method:
        query = query.filter(Payment.method == method)
    if status_filter:
        query = query.filter(Payment.status == status_filter)

    payments = query.all()
    results = [_to_admin_out(p) for p in payments]

    if search:
        s = search.strip().lower()
        results = [
            r for r in results
            if (r.client_name and s in r.client_name.lower())
            or (r.client_email and s in r.client_email.lower())
            or (r.order_number and s in r.order_number.lower())
        ]

    reverse = sort_dir.lower() != "asc"
    if sort_by == "amount":
        results.sort(key=lambda r: r.amount, reverse=reverse)
    elif sort_by == "client_name":
        results.sort(key=lambda r: (r.client_name or "").lower(), reverse=reverse)
    else:
        results.sort(key=lambda r: r.created_at, reverse=reverse)

    return results


@router.get("/{payment_id}", response_model=PaymentAdminOut)
def get_payment_detail(
    payment_id: str,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")
    return _to_admin_out(payment)


@router.post("/{payment_id}/review", response_model=PaymentAdminOut)
def review_payment(
    payment_id: str,
    payload: PaymentReviewDecision,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Validation/refus d'un paiement Interac (preuve de virement)."""
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


@router.post("/{payment_id}/refund", response_model=PaymentAdminOut)
def refund_payment_endpoint(
    payment_id: str,
    payload: PaymentRefundRequest,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Remboursement RÉEL. Stripe : appelle l'API Stripe (remboursement total si
    `amount` omis, partiel sinon). Interac : refusé ici — le retour de fonds
    se fait manuellement hors plateforme, puis l'admin ajuste le statut de
    la commande lui-même via Admin > Commandes.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Paiement introuvable.")

    payment = stripe_refund_payment(db, payment, payload.amount, payload.reason)

    log_action(
        db, actor_type="admin", actor_id=admin.id, action="refund_payment",
        target_type="payment", target_id=payment.id,
        details=f"Montant: {payload.amount or payment.amount} $ — Raison: {payload.reason or 'non précisée'}",
        ip_address=_client_ip(request),
    )

    return _to_admin_out(payment)


@router.get("/export/csv")
def export_payments_csv(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Exporte l'historique complet des paiements en CSV (pour comptabilité externe)."""
    import csv
    import io
    from fastapi.responses import StreamingResponse

    payments = db.query(Payment).order_by(Payment.created_at.desc()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Date", "Client", "Courriel", "Commande", "Services", "Sous-total", "TPS", "TVQ",
        "Total commande", "Méthode", "Type", "Montant payé", "Statut", "Carte", "Remboursé",
    ])
    for p in payments:
        out = _to_admin_out(p)
        writer.writerow([
            p.created_at.strftime("%Y-%m-%d %H:%M"),
            out.client_name or "", out.client_email or "", out.order_number or "",
            out.items_summary or "", out.order_subtotal or "", out.order_gst_amount or "",
            out.order_qst_amount or "", out.order_total or "",
            p.method.value, p.amount_type.value, p.amount, p.status.value,
            f"{p.card_brand or ''} {p.card_last4 or ''}".strip(),
            p.refunded_amount or "",
        ])

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=paiements_cyberteckq.csv"},
    )
