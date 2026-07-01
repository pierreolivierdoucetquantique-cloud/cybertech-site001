"""
Modèle de données : UploadedFile.

Centralise TOUS les fichiers téléversés sur la plateforme (preuves de
paiement Interac, images/vidéos du CMS, galeries de réalisations,
documents envoyés par l'admin à un client). Les fichiers eux-mêmes vivent
sur le Render Disk (chemin sous DATA_DIR/uploads/...) ; cette table ne
stocke que les métadonnées et les permissions d'accès.
"""
import datetime as dt

from sqlalchemy import Column, String, Integer, DateTime, Boolean

from app.database import Base
from app.models.client import gen_uuid


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, default=gen_uuid)

    # Catégorie logique : "payment_proof" | "cms_image" | "project_media" | "client_document"
    category = Column(String, nullable=False, index=True)

    # Chemin relatif sur le disk (sous DATA_DIR/uploads/), ex: "payment_proofs/2026/uuid.pdf"
    storage_path = Column(String, nullable=False, unique=True)

    original_filename = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, default=0)

    # Qui a le droit de voir ce fichier
    uploaded_by_type = Column(String, nullable=False)  # "admin" | "client"
    uploaded_by_id = Column(String, nullable=True)

    # Liens optionnels vers une commande / un client précis (pour les contrôles d'accès)
    related_order_id = Column(String, nullable=True, index=True)
    related_client_id = Column(String, nullable=True, index=True)

    is_public = Column(Boolean, default=False)  # True pour les images CMS publiques (portfolio, etc.)

    created_at = Column(DateTime, default=dt.datetime.utcnow)
