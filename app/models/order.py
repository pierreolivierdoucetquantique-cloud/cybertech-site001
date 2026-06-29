"""Modèle de données : Order (commande) et OrderItem."""
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
    REFUNDED = "refunded"


class ProductType(str, enum.Enum):
    WEBSITE = "website"
    MOBILE_APP = "mobile_app"
    MAINTENANCE = "maintenance"


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=gen_uuid)
    order_number = Column(String, unique=True, nullable=False, index=True)  # ex: ORD-26-00001

    client_id = Column(String, ForeignKey("clients.id"), nullable=False)

    product_type = Column(Enum(ProductType), nullable=False)
    product_name = Column(String, nullable=False)
    price = Column(Float, nullable=False)

    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.UNPAID)
    project_progress = Column(Integer, default=0)  # 0-100 %
    expected_delivery_date = Column(Date, nullable=True)  # date prévue de livraison (modifiable par l'admin)

    notes = Column(Text, nullable=True)  # notes internes admin

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    client = relationship("Client", back_populates="orders")
    invoice = relationship("Invoice", back_populates="order", uselist=False, cascade="all, delete-orphan")
    technical_form = relationship("TechnicalForm", back_populates="order", uselist=False)
    maintenance_contract = relationship("MaintenanceContract", back_populates="order", uselist=False, cascade="all, delete-orphan")


class OrderCounter(Base):
    """
    Compteur séquentiel pour les numéros de commande.
    Une seule ligne, verrouillée lors de l'incrémentation pour éviter les doublons.
    """
    __tablename__ = "order_counters"
    id = Column(String, primary_key=True, default=lambda: "singleton")
    last_number = Column(Integer, default=0, nullable=False)
    year = Column(Integer, nullable=False)
