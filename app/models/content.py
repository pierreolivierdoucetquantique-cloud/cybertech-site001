"""
Modèles de données pour le CMS : contenu éditable du site (clé/valeur)
+ FAQ dynamique. Permet à l'admin de modifier des textes sans toucher au code.
"""
import datetime as dt

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer

from app.database import Base
from app.models.client import gen_uuid


class ContentBlock(Base):
    """
    Bloc de contenu générique, identifié par une clé unique
    (ex: 'home.hero.title', 'services.cta.text').
    Le frontend (ou un futur rendu serveur) peut aller chercher ces valeurs.
    """
    __tablename__ = "content_blocks"

    id = Column(String, primary_key=True, default=gen_uuid)
    key = Column(String, unique=True, nullable=False, index=True)
    label = Column(String, nullable=True)  # nom lisible pour l'admin
    value = Column(Text, nullable=False, default="")
    content_type = Column(String, default="text")  # text | html | image_url | number

    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)


class FaqEntry(Base):
    __tablename__ = "faq_entries"

    id = Column(String, primary_key=True, default=gen_uuid)
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    display_order = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)


class PricingPlan(Base):
    __tablename__ = "pricing_plans"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False)
    price = Column(String, nullable=False)  # texte libre, ex: "1 300 $ CAD"
    features = Column(Text, nullable=False, default="[]")  # JSON liste de strings
    is_featured = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)

    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)


class RepeatableItem(Base):
    """
    Item générique appartenant à une liste éditable du site (ex: les étapes
    de "Notre histoire", les cartes de service, les items de la trust bar).

    `group_key` identifie la liste à laquelle l'item appartient
    (ex: 'home.story.steps', 'services.cards', 'services.process.steps').
    `fields` est un JSON dont les clés varient selon le groupe (ex: pour une
    étape d'histoire : {"tag": "...", "text": "...", "icon": "..."} ; pour
    une carte de service : {"title": "...", "text": "...", "icon": "...",
    "features": [...], "button_text": "...", "button_link": "..."}).

    Ce modèle unique remplace la nécessité de créer une table dédiée pour
    chaque type de liste répétée du site.
    """
    __tablename__ = "repeatable_items"

    id = Column(String, primary_key=True, default=gen_uuid)
    group_key = Column(String, nullable=False, index=True)
    fields = Column(Text, nullable=False, default="{}")  # JSON
    display_order = Column(Integer, default=0)
    is_published = Column(Boolean, default=True)

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)
