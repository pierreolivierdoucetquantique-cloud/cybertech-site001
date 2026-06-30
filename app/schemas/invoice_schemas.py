"""Schémas Pydantic : factures."""
import datetime as dt
from pydantic import BaseModel


class InvoiceOut(BaseModel):
    id: str
    invoice_number: str
    order_id: str
    subtotal: float
    gst_amount: float
    qst_amount: float
    total: float
    created_at: dt.datetime

    class Config:
        from_attributes = True
