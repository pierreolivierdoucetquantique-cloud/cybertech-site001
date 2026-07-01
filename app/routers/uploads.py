"""
Router : accès en lecture aux fichiers téléversés.

Règles d'accès :
- "cms_image" et "project_media" avec is_public=True : accessibles à tous (images du site public).
- "payment_proof" et "client_document" : accessibles uniquement à l'admin OU
  au client propriétaire (related_client_id). Jamais à un autre client.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_optional_client, get_current_admin
from app.models.client import Client
from app.models.upload import UploadedFile
from app.services.file_storage import absolute_path
from app.models.admin import Admin
from typing import Optional

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{file_id}")
def get_file(
    file_id: str,
    request: Request,
    db: Session = Depends(get_db),
    client: Optional[Client] = Depends(get_optional_client),
):
    record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Fichier introuvable.")

    if record.is_public:
        return FileResponse(absolute_path(record), filename=record.original_filename)

    # Tente une auth admin si présente (sans bloquer si absente)
    is_admin = False
    try:
        get_current_admin(request, db)
        is_admin = True
    except HTTPException:
        is_admin = False

    if is_admin:
        return FileResponse(absolute_path(record), filename=record.original_filename)

    if client and record.related_client_id == client.id:
        return FileResponse(absolute_path(record), filename=record.original_filename)

    raise HTTPException(status_code=403, detail="Accès refusé à ce fichier.")
