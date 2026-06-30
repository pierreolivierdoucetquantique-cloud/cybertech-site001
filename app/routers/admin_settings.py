"""
Router : réglages globaux de la plateforme, gérés par l'admin.

v9.11 — premier réglage : activer/désactiver TPS+TVQ sur les NOUVELLES
commandes (n'affecte jamais les commandes déjà créées, dont les montants
sont figés au moment de la création, comme une facture déjà émise).
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.services.audit import log_action
from app.services.settings_service import is_taxes_enabled, set_taxes_enabled

router = APIRouter(prefix="/api/admin/settings", tags=["admin-settings"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


class TaxesSettingOut(BaseModel):
    enable_tps_tvq: bool


class TaxesSettingUpdate(BaseModel):
    enable_tps_tvq: bool


@router.get("/taxes", response_model=TaxesSettingOut)
def get_taxes_setting(
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return TaxesSettingOut(enable_tps_tvq=is_taxes_enabled(db))


@router.put("/taxes", response_model=TaxesSettingOut)
def update_taxes_setting(
    payload: TaxesSettingUpdate,
    request: Request,
    admin: Admin = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    set_taxes_enabled(db, payload.enable_tps_tvq)
    log_action(
        db, actor_type="admin", actor_id=admin.id, action="update_taxes_setting",
        target_type="settings", target_id="enable_tps_tvq",
        details=f"enable_tps_tvq={payload.enable_tps_tvq}",
        ip_address=_client_ip(request),
    )
    return TaxesSettingOut(enable_tps_tvq=payload.enable_tps_tvq)
