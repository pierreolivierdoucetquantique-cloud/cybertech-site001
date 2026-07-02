"""Router : profil admin (consultation, changement de mot de passe)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin, AdminSession
from app.schemas.admin_schemas import AdminOut
from app.schemas.client_schemas import validate_password_strength
from app.utils.security import verify_password, hash_password
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin/profile", tags=["admin-profile"])


class AdminPasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v):
        return validate_password_strength(v)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.get("/me", response_model=AdminOut)
def get_my_admin_profile(admin: Admin = Depends(get_current_admin)):
    return admin


@router.post("/change-password")
def change_admin_password(
    payload: AdminPasswordChange,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect.")

    admin.password_hash = hash_password(payload.new_password)

    # Révoque toutes les sessions admin actives (y compris la session courante,
    # par sécurité maximale après un changement de mot de passe)
    db.query(AdminSession).filter(AdminSession.admin_id == admin.id).update({"revoked": True})
    db.commit()

    log_action(db, actor_type="admin", actor_id=admin.id, action="change_password", ip_address=_client_ip(request))
    return {"message": "Mot de passe modifié. Veuillez vous reconnecter."}
