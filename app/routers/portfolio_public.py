"""Router : portfolio public (projets publiés, visibles sans authentification)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.project import Project
from app.schemas.project_schemas import ProjectOut

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("", response_model=list[ProjectOut])
def list_published_projects(db: Session = Depends(get_db)):
    """Retourne uniquement les projets publiés, triés pour affichage public."""
    projects = (
        db.query(Project)
        .filter(Project.is_published == True)  # noqa: E712
        .order_by(Project.display_order.asc(), Project.created_at.desc())
        .all()
    )
    return projects
