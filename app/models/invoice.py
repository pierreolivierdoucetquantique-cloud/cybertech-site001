"""Modèle de données : Invoice (facture)."""
import enum
import datetime as dt

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.client import gen_uuid


class InvoiceStatus(str, enum.Enum):
    DEPOSIT_PAID = "Deposit Paid"
    PAID_IN_FULL = "Paid in Full"
    REFUNDED = "Refunded"
    PARTIALLY_REFUNDED = "Partially Refunded"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=gen_uuid)
    invoice_number = Column(String, unique=True, nullable=False, index=True)  # ex: CTQ-26-00001

    order_id = Column(String, ForeignKey("orders.id"), nullable=False, unique=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False)

    subtotal = Column(Float, nullable=False)
    gst_amount = Column(Float, nullable=False, default=0.0)
    qst_amount = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False)

    # --- Logique de facturation automatique (dépôt 40% / paiement complet) ---
    # amount_paid / remaining_balance sont recalculés automatiquement à chaque
    # paiement confirmé (voir app/services/billing.py:sync_invoice_for_order).
    # deposit_amount est NULL lorsque la facture est payée intégralement (Case B) —
    # ne doit alors JAMAIS être affiché (ni en PDF, ni dans l'espace client).
    deposit_amount = Column(Float, nullable=True)
    amount_paid = Column(Float, nullable=False, default=0.0)
    remaining_balance = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False, default=InvoiceStatus.DEPOSIT_PAID.value)

    pdf_path = Column(String, nullable=True)  # chemin du PDF sur le disk

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    order = relationship("Order", back_populates="invoice")
    client = relationship("Client")


class InvoiceCounter(Base):
    """
    Compteur séquentiel dédié aux factures (distinct des commandes).
    Une seule ligne par année ; l'incrémentation se fait dans une transaction
    avec verrou pour garantir l'unicité même en cas de requêtes concurrentes.
    """
    __tablename__ = "invoice_counters"
    id = Column(String, primary_key=True, default=lambda: "singleton")
    last_number = Column(Integer, default=0, nullable=False)
    year = Column(Integer, nullable=False)
