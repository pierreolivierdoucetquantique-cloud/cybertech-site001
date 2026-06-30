"""Modèle de données : Project (réalisations affichées sur le portfolio public)."""
import datetime as dt

from sqlalchemy import Column, String, Text, Boolean, DateTime, Date

from app.database import Base
from app.models.client import gen_uuid


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=gen_uuid)

    title = Column(String, nullable=False)
    client_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    preview_image_path = Column(String, nullable=True)
    gallery_images = Column(Text, nullable=True)  # JSON: liste de chemins
    video_url = Column(String, nullable=True)
    technologies = Column(String, nullable=True)  # ex: "HTML, CSS, JS"
    external_link = Column(String, nullable=True)
    completion_date = Column(Date, nullable=True)

    is_published = Column(Boolean, default=False)  # Draft / Published
    display_order = Column(String, default="0")  # pour trier manuellement

    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)
