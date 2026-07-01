"""
Service de stockage de fichiers.

Tous les fichiers téléversés (preuves de paiement, images CMS, galeries de
réalisations, documents admin -> client) sont écrits sur le Render Disk,
dans settings.UPLOADS_DIR, organisés par catégorie et par année :

  data/uploads/payment_proofs/2026/<uuid>.pdf
  data/uploads/cms_images/2026/<uuid>.jpg
  data/uploads/project_media/2026/<uuid>.mp4
  data/uploads/client_documents/2026/<uuid>.pdf

Le nom de fichier sur disque est toujours un UUID régénéré (jamais le nom
original du client) pour éviter les collisions et les chemins malicieux.
"""
import os
import uuid
import datetime as dt

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.upload import UploadedFile

# Extensions autorisées par catégorie (whitelist stricte).
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".doc", ".docx", ".xls", ".xlsx"}

CATEGORY_ALLOWED_EXTENSIONS = {
    "payment_proof": {".pdf", ".jpg", ".jpeg", ".png", ".webp"},
    "cms_image": IMAGE_EXTENSIONS,
    "project_media": IMAGE_EXTENSIONS | VIDEO_EXTENSIONS,
    "client_document": DOCUMENT_EXTENSIONS,
}

CATEGORY_SUBDIR = {
    "payment_proof": "payment_proofs",
    "cms_image": "cms_images",
    "project_media": "project_media",
    "client_document": "client_documents",
}


def _safe_extension(filename: str) -> str:
    _, ext = os.path.splitext(filename or "")
    return ext.lower()


async def save_upload(
    db: Session,
    file: UploadFile,
    category: str,
    uploaded_by_type: str,
    uploaded_by_id: str | None = None,
    related_order_id: str | None = None,
    related_client_id: str | None = None,
    is_public: bool = False,
) -> UploadedFile:
    """
    Valide, écrit sur disque, et enregistre les métadonnées d'un fichier
    téléversé. Lève HTTPException(400/413) si le fichier est invalide.
    """
    if category not in CATEGORY_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Catégorie de fichier invalide.")

    ext = _safe_extension(file.filename or "")
    allowed = CATEGORY_ALLOWED_EXTENSIONS[category]
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non autorisé. Extensions acceptées : {', '.join(sorted(allowed))}",
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Le fichier est vide.")
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Le fichier dépasse la taille maximale autorisée ({settings.MAX_UPLOAD_SIZE_MB} Mo).",
        )

    year = str(dt.datetime.utcnow().year)
    subdir = os.path.join(CATEGORY_SUBDIR[category], year)
    abs_dir = os.path.join(settings.UPLOADS_DIR, subdir)
    os.makedirs(abs_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4()}{ext}"
    storage_path = os.path.join(subdir, stored_name)
    abs_path = os.path.join(settings.UPLOADS_DIR, storage_path)

    with open(abs_path, "wb") as f:
        f.write(contents)

    record = UploadedFile(
        category=category,
        storage_path=storage_path,
        original_filename=file.filename or stored_name,
        content_type=file.content_type,
        size_bytes=len(contents),
        uploaded_by_type=uploaded_by_type,
        uploaded_by_id=uploaded_by_id,
        related_order_id=related_order_id,
        related_client_id=related_client_id,
        is_public=is_public,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def absolute_path(record: UploadedFile) -> str:
    return os.path.join(settings.UPLOADS_DIR, record.storage_path)


def delete_upload(db: Session, record: UploadedFile) -> None:
    """Supprime le fichier physique (best-effort) puis son enregistrement."""
    try:
        path = absolute_path(record)
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
    db.delete(record)
    db.commit()
