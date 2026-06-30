"""Modèle de données : TechnicalForm (questionnaire technique après commande)."""
import datetime as dt

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.client import gen_uuid


class TechnicalForm(Base):
    __tablename__ = "technical_forms"

    id = Column(String, primary_key=True, default=gen_uuid)

    # v9.11 : lié à un OrderItem (un service précis du panier), plus à Order
    order_item_id = Column(String, ForeignKey("order_items.id"), nullable=False, unique=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False)

    company_name = Column(String, nullable=True)
    business_sector = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    objectives = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    pages_required = Column(Text, nullable=True)
    desired_colors = Column(String, nullable=True)
    has_existing_logo = Column(Boolean, default=False)
    has_images = Column(Boolean, default=False)

    # Fonctionnalités désirées (stockées en CSV simple ou JSON)
    feature_booking = Column(Boolean, default=False)
    feature_payment = Column(Boolean, default=False)
    feature_blog = Column(Boolean, default=False)
    feature_gallery = Column(Boolean, default=False)
    feature_shop = Column(Boolean, default=False)
    languages = Column(String, nullable=True)  # ex: "Français, Anglais"

    hosting = Column(String, nullable=True)
    domain_name = Column(String, nullable=True)
    reference_websites = Column(Text, nullable=True)
    additional_notes = Column(Text, nullable=True)

    # --- Section Hébergement Web (v9.9) ---
    has_current_hosting = Column(Boolean, nullable=True)       # Q1 : a un hébergement actuellement ?
    hosting_provider = Column(String, nullable=True)           # affiché si Q1 = oui
    hosting_access_details = Column(Text, nullable=True)       # affiché si Q1 = oui
    wants_new_hosting = Column(Boolean, nullable=True)         # Q2 : veut un nouvel hébergement de CTQ ?
    has_domain_name = Column(Boolean, nullable=True)           # Q3 : possède déjà un nom de domaine ?
    wants_domain_help = Column(Boolean, nullable=True)         # Q4 : besoin d'aide pour acheter un domaine ?
    wants_website_transfer = Column(Boolean, nullable=True)    # Q5 : veut transférer un site existant ?

    submitted_at = Column(DateTime, default=dt.datetime.utcnow)

    order_item = relationship("OrderItem", back_populates="technical_form")
    client = relationship("Client", back_populates="technical_forms")
