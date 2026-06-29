"""Schémas Pydantic : marketplace de services et commandes."""
import datetime as dt
from typing import Optional

from pydantic import BaseModel

from app.models.order import OrderStatus, PaymentStatus, ProductType


class ProductOut(BaseModel):
    """Un produit catalogue (statique pour l'instant, gérable via CMS plus tard)."""
    product_type: ProductType
    name: str
    description: str
    price: float
    currency: str = "CAD"
    image_url: Optional[str] = None
    features: list[str] = []


class OrderCreate(BaseModel):
    product_type: ProductType


class OrderOut(BaseModel):
    id: str
    order_number: str
    product_type: ProductType
    product_name: str
    price: float
    status: OrderStatus
    payment_status: PaymentStatus
    project_progress: int
    progress_step_label: str
    progress_color: str
    expected_delivery_date: Optional[dt.date] = None
    updated_at: dt.datetime
    created_at: dt.datetime
    has_technical_form: bool = False
    has_invoice: bool = False
    payment_unlocked: bool = False
    has_maintenance_contract: bool = False
    maintenance_contract_signed: bool = False

    class Config:
        from_attributes = True


class OrderAdminUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    project_progress: Optional[int] = None
    expected_delivery_date: Optional[dt.date] = None
    notes: Optional[str] = None
