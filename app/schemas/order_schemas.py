"""Schémas Pydantic : marketplace de services et commandes (panier multi-services, v9.11)."""
import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field

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


class CartItemIn(BaseModel):
    """Un service à ajouter au panier au moment de la création de la commande."""
    product_type: ProductType
    quantity: int = Field(default=1, ge=1, le=20)


class OrderCreate(BaseModel):
    """
    v9.11 : une commande peut contenir plusieurs services (panier).
    Compatible avec l'ancien format à 1 seul produit (product_type) pour ne
    pas casser un éventuel appel client déjà en cache, mais le format
    recommandé est `items`.
    """
    items: Optional[list[CartItemIn]] = None
    product_type: Optional[ProductType] = None  # rétrocompatibilité : 1 seul item

    def resolved_items(self) -> list[CartItemIn]:
        if self.items:
            return self.items
        if self.product_type:
            return [CartItemIn(product_type=self.product_type, quantity=1)]
        return []


class OrderItemOut(BaseModel):
    id: str
    product_type: ProductType
    product_name: str
    price: float
    project_progress: int
    progress_step_label: str
    progress_color: str
    expected_delivery_date: Optional[dt.date] = None
    has_technical_form: bool = False
    has_invoice_unused: bool = False  # placeholder non utilisé, conservé pour stabilité de schéma
    has_maintenance_contract: bool = False
    maintenance_contract_signed: bool = False

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: str
    order_number: str
    items: list[OrderItemOut]
    subtotal: float
    gst_amount: float
    qst_amount: float
    total: float
    taxes_applied: bool
    status: OrderStatus
    payment_status: PaymentStatus
    updated_at: dt.datetime
    created_at: dt.datetime
    has_invoice: bool = False
    payment_unlocked: bool = False
    amount_paid: float = 0.0
    remaining_balance: float = 0.0

    class Config:
        from_attributes = True


class OrderItemAdminUpdate(BaseModel):
    project_progress: Optional[int] = Field(default=None, ge=0, le=100)
    expected_delivery_date: Optional[dt.date] = None


class OrderAdminUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    notes: Optional[str] = None
