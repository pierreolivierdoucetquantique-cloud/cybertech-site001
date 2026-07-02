"""Router : gestion des projets par l'admin (CRUD complet)."""
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.project import Project
from app.schemas.project_schemas import ProjectCreate, ProjectUpdate, ProjectOut
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin/projects", tags=["admin-projects"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("", response_model=list[ProjectOut])
def list_all_projects(admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Liste TOUS les projets (brouillons et publiés), pour l'interface admin."""
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    log_action(db, actor_type="admin", actor_id=admin.id, action="create_project", target_type="project", target_id=project.id, ip_address=_client_ip(request))
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    project.updated_at = dt.datetime.utcnow()
    db.commit()
    db.refresh(project)

    log_action(db, actor_type="admin", actor_id=admin.id, action="update_project", target_type="project", target_id=project.id, ip_address=_client_ip(request))
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projet introuvable.")
    db.delete(project)
    db.commit()
    log_action(db, actor_type="admin", actor_id=admin.id, action="delete_project", target_type="project", target_id=project_id, ip_address=_client_ip(request))
    return {"message": "Projet supprimé."}
