"""
Router : upload de médias par l'admin (CMS sans code).

Permet à l'admin de :
- téléverser une image générique (CMS : page d'accueil, services, etc.)
- ajouter une image/vidéo à la galerie d'une réalisation
- envoyer un document à un client précis
- retirer une image de la galerie d'une réalisation
"""
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.project import Project
from app.models.client import Client
from app.models.upload import UploadedFile
from app.services.file_storage import save_upload, delete_upload
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin/media", tags=["admin-media"])


@router.post("/cms-image")
async def upload_cms_image(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """
    Téléverse une image générique destinée au CMS (arrière-plans, bannières,
    images de services, etc.). Retourne l'URL publique à coller dans un bloc
    de contenu ou un champ du panneau admin.
    """
    record = await save_upload(
        db, file, category="cms_image",
        uploaded_by_type="admin", uploaded_by_id=admin.id,
        is_public=True,
    )
    log_action(db, actor_type="admin", actor_id=admin.id, action="upload_cms_image", target_type="upload", target_id=record.id)
    return {"file_id": record.id, "url": f"/api/files/{record.id}"}


@router.post("/projects/{project_id}/gallery")
async def add_project_gallery_media(
    project_id: str,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    """Ajoute une image ou une vidéo à la galerie d'une réalisation."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    record = await save_upload(
        db, file, category="project_media",
        uploaded_by_type="admin", uploaded_by_id=admin.id,
        is_public=True,
    )

    current = json.loads(project.gallery_images) if project.gallery_images else []
    current.append(record.id)
    project.gallery_images = json.dumps(current)
    db.commit()

    log_action(db, actor_type="admin", actor_id=admin.id, action="add_project_media", target_type="project", target_id=project.id)
    return {"file_id": record.id, "url": f"/api/files/{record.id}", "gallery_images": current}


@router.delete("/projects/{project_id}/gallery/{file_id}")
def remove_project_gallery_media(
    project_id: str,
    file_id: str,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    current = json.loads(project.gallery_images) if project.gallery_images else []
    if file_id not in current:
        raise HTTPException(status_code=404, detail="Ce fichier ne fait pas partie de la galerie.")
    current.remove(file_id)
    project.gallery_images = json.dumps(current)
    db.commit()

    record = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if record:
        delete_upload(db, record)

    log_action(db, actor_type="admin", actor_id=admin.id, action="remove_project_media", target_type="project", target_id=project.id)
    return {"gallery_images": current}


@router.post("/clients/{client_id}/documents")
async def send_document_to_client(
    client_id: str,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    order_id: str = Form(None),
):
    """L'admin téléverse un document destiné à un client précis (visible uniquement par ce client et l'admin)."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client introuvable.")

    record = await save_upload(
        db, file, category="client_document",
        uploaded_by_type="admin", uploaded_by_id=admin.id,
        related_client_id=client.id, related_order_id=order_id,
    )
    log_action(db, actor_type="admin", actor_id=admin.id, action="send_client_document", target_type="client", target_id=client.id, details=record.original_filename)
    return {"file_id": record.id, "url": f"/api/files/{record.id}", "filename": record.original_filename}


@router.get("/clients/{client_id}/documents")
def list_client_documents(
    client_id: str,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    docs = (
        db.query(UploadedFile)
        .filter(UploadedFile.related_client_id == client_id, UploadedFile.category == "client_document")
        .order_by(UploadedFile.created_at.desc())
        .all()
    )
    return [
        {"file_id": d.id, "url": f"/api/files/{d.id}", "filename": d.original_filename, "created_at": d.created_at}
        for d in docs
    ]
