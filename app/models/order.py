"""
Modèle de données : Order (panier de commande) et OrderItem (service individuel).

CHANGEMENT v9.11 — Panier multi-services :
Avant cette version, une Order représentait un seul service (product_type,
product_name, price directement sur Order). À partir de v9.11, Order devient
le PANIER : elle regroupe un ou plusieurs OrderItem, chacun représentant un
service distinct (Site Web, Application Mobile, ou Maintenance), avec son
propre prix, son propre questionnaire technique OU contrat de maintenance, et
sa propre progression de projet.

Un client peut ajouter plusieurs unités du même service dans un seul panier
(ex : 2x Site Web) — il n'y a donc PAS de contrainte d'unicité sur
(order_id, product_type).

Le paiement (dépôt 40% / solde) reste calculé sur la commande complète
(Order.total), pas item par item : un seul dépôt/paiement couvre tout le
panier, ce qui correspond à la réalité d'un seul virement Interac ou d'une
seule transaction Stripe par client.
"""
import enum
import datetime as dt

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum, Integer, Text, Date
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.client import gen_uuid


class OrderStatus(str, enum.Enum):
    PENDING = "pending"          # en attente (dépôt non reçu / non confirmé)
    PROCESSING = "processing"    # en cours de réalisation
    DELIVERED = "delivered"      # livré
    CANCELLED = "cancelled"      # annulé
    ARCHIVED = "archived"        # archivé


class PaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    DEPOSIT_PAID = "deposit_paid"   # dépôt de 40% reçu
    PAID = "paid"                   # payé en totalité
    REFUNDED = "refunded"           # remboursé (total)
    PARTIALLY_REFUNDED = "partially_refunded"  # remboursé partiellement


class ProductType(str, enum.Enum):
    WEBSITE = "website"
    MOBILE_APP = "mobile_app"
    MAINTENANCE = "maintenance"


class Order(Base):
    """
    Représente le PANIER d'une commande client : un regroupement d'un ou
    plusieurs OrderItem, avec un total global, un statut de paiement global,
    et un historique de paiements (dépôt/solde) qui s'applique à l'ensemble.
    """
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=gen_uuid)
    order_number = Column(String, unique=True, nullable=False, index=True)  # ex: ORD-26-00001

    client_id = Column(String, ForeignKey("clients.id"), nullable=False)

    # --- Montants (figés au moment de la création du panier, comme une facture) ---
    subtotal = Column(Float, nullable=False, default=0.0)
    taxes_applied = Column(String, nullable=False, default="true")  # "true"/"false" — copie du réglage global au moment de la commande
    gst_amount = Column(Float, nullable=False, default=0.0)
    qst_amount = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False, default=0.0)

    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.UNPAID)

    notes = Column(Text, nullable=True)  # notes internes admin

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    client = relationship("Client", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", order_by="OrderItem.created_at")
    invoice = relationship("Invoice", back_populates="order", uselist=False, cascade="all, delete-orphan")

    def recalculate_totals(self, gst_rate: float, qst_rate: float, apply_taxes: bool) -> None:
        """Recalcule subtotal/taxes/total à partir des items actuels du panier."""
        self.subtotal = round(sum(item.price for item in self.items), 2)
        if apply_taxes:
            self.gst_amount = round(self.subtotal * gst_rate, 2)
            self.qst_amount = round(self.subtotal * qst_rate, 2)
        else:
            self.gst_amount = 0.0
            self.qst_amount = 0.0
        self.taxes_applied = "true" if apply_taxes else "false"
        self.total = round(self.subtotal + self.gst_amount + self.qst_amount, 2)


class OrderItem(Base):
    """
    Un service individuel à l'intérieur d'un panier (Order). Porte sa propre
    progression de projet, sa date de livraison prévue, et est relié à SON
    PROPRE questionnaire technique ou contrat de maintenance (selon le type).
    """
    __tablename__ = "order_items"

    id = Column(String, primary_key=True, default=gen_uuid)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)

    product_type = Column(Enum(ProductType), nullable=False)
    product_name = Column(String, nullable=False)
    price = Column(Float, nullable=False)

    project_progress = Column(Integer, default=0)  # 0-100 %
    expected_delivery_date = Column(Date, nullable=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    order = relationship("Order", back_populates="items")
    technical_form = relationship("TechnicalForm", back_populates="order_item", uselist=False, cascade="all, delete-orphan")
    maintenance_contract = relationship("MaintenanceContract", back_populates="order_item", uselist=False, cascade="all, delete-orphan")


class OrderCounter(Base):
    """
    Compteur séquentiel pour les numéros de commande.
    Une seule ligne, verrouillée lors de l'incrémentation pour éviter les doublons.
    """
    __tablename__ = "order_counters"
    id = Column(String, primary_key=True, default=lambda: "singleton")
    last_number = Column(Integer, default=0, nullable=False)
    year = Column(Integer, nullable=False)
