"""Modèle de données : Payment (tentative/preuve de paiement Interac ou Stripe)."""
import enum
import datetime as dt

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.client import gen_uuid


class PaymentMethod(str, enum.Enum):
    INTERAC = "interac"
    STRIPE = "stripe"


class PaymentAmountType(str, enum.Enum):
    DEPOSIT = "deposit"   # 40% du prix de la commande
    FULL = "full"         # montant total (aucun dépôt préalable)
    BALANCE = "balance"   # solde restant (60%) après un dépôt déjà payé


class PaymentRequestStatus(str, enum.Enum):
    PENDING_PROOF = "pending_proof"          # Interac : en attente que le client téléverse sa preuve
    PENDING_VALIDATION = "pending_validation"  # Interac : preuve reçue, en attente de validation admin
    APPROVED = "approved"                     # Interac validé par l'admin, ou Stripe confirmé
    REJECTED = "rejected"                     # Interac refusé par l'admin
    STRIPE_INITIATED = "stripe_initiated"      # session Stripe créée, paiement non confirmé encore
    REFUNDED = "refunded"                      # remboursé (total) après avoir été approuvé
    CANCELLED = "cancelled"                    # annulé avant complétion (ex: session Stripe abandonnée)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=gen_uuid)

    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False, index=True)

    method = Column(Enum(PaymentMethod), nullable=False)
    amount_type = Column(Enum(PaymentAmountType), nullable=False)
    amount = Column(Float, nullable=False)

    status = Column(Enum(PaymentRequestStatus), default=PaymentRequestStatus.PENDING_PROOF)

    # Interac
    proof_file_id = Column(String, ForeignKey("uploaded_files.id"), nullable=True)
    admin_review_note = Column(Text, nullable=True)
    reviewed_by_admin_id = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Stripe
    stripe_checkout_session_id = Column(String, nullable=True, index=True)
    stripe_payment_intent_id = Column(String, nullable=True)
    card_brand = Column(String, nullable=True)   # ex: "visa", "mastercard" — informatif seulement, Stripe reste la méthode
    card_last4 = Column(String, nullable=True)

    # Remboursement (v9.11)
    refunded_amount = Column(Float, nullable=True)
    refund_reason = Column(Text, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    stripe_refund_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    order = relationship("Order")
    client = relationship("Client")
    proof_file = relationship("UploadedFile")
