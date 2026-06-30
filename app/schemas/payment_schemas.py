"""Schémas Pydantic : paiements (Interac et Stripe), liés au panier complet (v9.11)."""
import datetime as dt
from typing import Optional

from pydantic import BaseModel

from app.models.payment import PaymentMethod, PaymentAmountType, PaymentRequestStatus


class InteracPaymentCreate(BaseModel):
    order_id: str
    amount_type: PaymentAmountType


class StripeCheckoutCreate(BaseModel):
    order_id: str
    amount_type: PaymentAmountType


class PaymentOut(BaseModel):
    id: str
    order_id: str
    method: PaymentMethod
    amount_type: PaymentAmountType
    amount: float
    status: PaymentRequestStatus
    proof_file_id: Optional[str] = None
    admin_review_note: Optional[str] = None
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    refunded_amount: Optional[float] = None
    refund_reason: Optional[str] = None
    refunded_at: Optional[dt.datetime] = None
    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        from_attributes = True


class PaymentAdminOut(PaymentOut):
    client_id: str
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    order_number: Optional[str] = None
    # Montants du panier complet (pas seulement de ce paiement) — utile pour
    # l'affichage en colonnes dans Admin > Paiements (sous-total/TPS/TVQ/total).
    order_subtotal: Optional[float] = None
    order_gst_amount: Optional[float] = None
    order_qst_amount: Optional[float] = None
    order_total: Optional[float] = None
    items_summary: Optional[str] = None


class PaymentReviewDecision(BaseModel):
    approve: bool
    note: Optional[str] = None


class PaymentRefundRequest(BaseModel):
    amount: Optional[float] = None  # None = remboursement total
    reason: Optional[str] = None
