"""Schémas Pydantic : factures."""
import datetime as dt
from typing import Optional
from pydantic import BaseModel


class InvoiceOut(BaseModel):
    id: str
    invoice_number: str
    order_id: str
    order_number: Optional[str] = None
    subtotal: float
    gst_amount: float
    qst_amount: float
    total: float
    deposit_amount: Optional[float] = None      # 40% du total
    balance_remaining: Optional[float] = None   # total - montants confirmés
    payment_status: Optional[str] = None        # unpaid / deposit_paid / paid / refunded
    payment_method: Optional[str] = None        # interac / stripe (dernier paiement confirmé)
    transaction_id: Optional[str] = None        # stripe_payment_intent_id ou id Interac
    payment_date: Optional[dt.datetime] = None  # date du dernier paiement confirmé
    created_at: dt.datetime

    class Config:
        from_attributes = True
