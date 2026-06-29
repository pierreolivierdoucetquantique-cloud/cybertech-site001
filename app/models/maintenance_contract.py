"""
Modèle de données : MaintenanceContract.

Remplace le questionnaire technique pour les commandes de type MAINTENANCE.
Un contrat est d'abord créé en statut DRAFT (consultable/modifiable côté
client tant qu'il n'est pas signé), puis verrouillé définitivement (LOCKED)
une fois la signature électronique apposée — à partir de ce moment, plus
aucun champ ne peut être modifié, conformément à la valeur probante d'un
document signé.
"""
import enum
import datetime as dt

from sqlalchemy import Column, String, Float, DateTime, Date, ForeignKey, Enum, Text, Boolean, Integer
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.client import gen_uuid


class ContractStatus(str, enum.Enum):
    DRAFT = "draft"      # créé, en attente de signature
    SIGNED = "signed"    # signé par le client, verrouillé, PDF généré


class MaintenanceContract(Base):
    __tablename__ = "maintenance_contracts"

    id = Column(String, primary_key=True, default=gen_uuid)
    contract_number = Column(String, unique=True, nullable=False, index=True)  # ex: CTQ-MNT-26-00001

    order_id = Column(String, ForeignKey("orders.id"), nullable=False, unique=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False, index=True)

    status = Column(Enum(ContractStatus), default=ContractStatus.DRAFT, nullable=False)

    # --- Informations du contrat (capturées/confirmées avant signature) ---
    client_full_name = Column(String, nullable=False)
    company_name = Column(String, nullable=True)
    client_email = Column(String, nullable=False)
    client_phone = Column(String, nullable=True)
    website_concerned = Column(String, nullable=True)  # URL ou nom du site concerné

    maintenance_plan = Column(String, nullable=False, default="Maintenance annuelle Cyber Teck Q")
    annual_price = Column(Float, nullable=False)
    contract_duration_months = Column(Integer, nullable=False, default=12)

    effective_date = Column(Date, nullable=False)
    expiration_date = Column(Date, nullable=False)

    # --- Signature électronique ---
    signer_name = Column(String, nullable=True)
    client_signature_data = Column(Text, nullable=True)   # image signature (data URL base64) ou nom tapé
    signature_type = Column(String, nullable=True)        # "drawn" | "typed"
    accepted_terms = Column(Boolean, default=False)
    signed_at = Column(DateTime, nullable=True)
    signed_ip_address = Column(String, nullable=True)

    admin_signature_name = Column(String, nullable=True)
    admin_signed_at = Column(DateTime, nullable=True)

    # --- Document final ---
    pdf_path = Column(String, nullable=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    order = relationship("Order", back_populates="maintenance_contract")
    client = relationship("Client")


class MaintenanceContractCounter(Base):
    """Compteur séquentiel dédié aux contrats de maintenance (CTQ-MNT-AA-NNNNN)."""
    __tablename__ = "maintenance_contract_counters"
    id = Column(String, primary_key=True, default=lambda: "singleton")
    last_number = Column(Integer, default=0, nullable=False)
    year = Column(Integer, nullable=False)
