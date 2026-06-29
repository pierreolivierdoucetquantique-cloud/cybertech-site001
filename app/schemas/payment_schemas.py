"""Schémas Pydantic : paiements (Interac et Stripe)."""
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
    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        from_attributes = True


class PaymentAdminOut(PaymentOut):
    client_id: str
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    order_number: Optional[str] = None


class PaymentReviewDecision(BaseModel):
    approve: bool
    note: Optional[str] = None
