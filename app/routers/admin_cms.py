"""Router : CMS admin — édition visuelle du contenu du site, sans code."""
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.admin import Admin
from app.models.content import FaqEntry, PricingPlan, ContentBlock, RepeatableItem
from app.schemas.cms_schemas import (
    FaqEntryCreate, FaqEntryUpdate, FaqEntryOut,
    PricingPlanCreate, PricingPlanUpdate, PricingPlanOut,
    ContentBlockOut, ContentBlockUpdate,
    RepeatableItemCreate, RepeatableItemUpdate, RepeatableItemOut, RepeatableItemReorder,
)
from app.services.audit import log_action

router = APIRouter(prefix="/api/admin/cms", tags=["admin-cms"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ---------- FAQ ----------

@router.get("/faq", response_model=list[FaqEntryOut])
def list_all_faq(admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(FaqEntry).order_by(FaqEntry.display_order.asc()).all()


@router.post("/faq", response_model=FaqEntryOut, status_code=201)
def create_faq(payload: FaqEntryCreate, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    entry = FaqEntry(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    log_action(db, actor_type="admin", actor_id=admin.id, action="create_faq", target_type="faq", target_id=entry.id, ip_address=_client_ip(request))
    return entry


@router.put("/faq/{faq_id}", response_model=FaqEntryOut)
def update_faq(faq_id: str, payload: FaqEntryUpdate, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    entry = db.query(FaqEntry).filter(FaqEntry.id == faq_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Question FAQ introuvable.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    log_action(db, actor_type="admin", actor_id=admin.id, action="update_faq", target_type="faq", target_id=entry.id, ip_address=_client_ip(request))
    return entry


@router.delete("/faq/{faq_id}")
def delete_faq(faq_id: str, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    entry = db.query(FaqEntry).filter(FaqEntry.id == faq_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Question FAQ introuvable.")
    db.delete(entry)
    db.commit()
    log_action(db, actor_type="admin", actor_id=admin.id, action="delete_faq", target_type="faq", target_id=faq_id, ip_address=_client_ip(request))
    return {"message": "Question supprimée."}


# ---------- Tarifs ----------

@router.get("/pricing", response_model=list[PricingPlanOut])
def list_all_pricing(admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(PricingPlan).order_by(PricingPlan.display_order.asc()).all()


@router.post("/pricing", response_model=PricingPlanOut, status_code=201)
def create_pricing(payload: PricingPlanCreate, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["features"] = json.dumps(data["features"], ensure_ascii=False)
    plan = PricingPlan(**data)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    log_action(db, actor_type="admin", actor_id=admin.id, action="create_pricing", target_type="pricing", target_id=plan.id, ip_address=_client_ip(request))
    return plan


@router.put("/pricing/{plan_id}", response_model=PricingPlanOut)
def update_pricing(plan_id: str, payload: PricingPlanUpdate, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    plan = db.query(PricingPlan).filter(PricingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Forfait introuvable.")
    updates = payload.model_dump(exclude_unset=True)
    if "features" in updates:
        updates["features"] = json.dumps(updates["features"], ensure_ascii=False)
    for field, value in updates.items():
        setattr(plan, field, value)
    db.commit()
    db.refresh(plan)
    log_action(db, actor_type="admin", actor_id=admin.id, action="update_pricing", target_type="pricing", target_id=plan.id, ip_address=_client_ip(request))
    return plan


@router.delete("/pricing/{plan_id}")
def delete_pricing(plan_id: str, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    plan = db.query(PricingPlan).filter(PricingPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Forfait introuvable.")
    db.delete(plan)
    db.commit()
    log_action(db, actor_type="admin", actor_id=admin.id, action="delete_pricing", target_type="pricing", target_id=plan_id, ip_address=_client_ip(request))
    return {"message": "Forfait supprimé."}


# ---------- Blocs de contenu génériques (textes, titres, etc.) ----------

@router.get("/content", response_model=list[ContentBlockOut])
def list_content_blocks(admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    return db.query(ContentBlock).order_by(ContentBlock.key.asc()).all()


@router.put("/content/{key}", response_model=ContentBlockOut)
def upsert_content_block(key: str, payload: ContentBlockUpdate, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    block = db.query(ContentBlock).filter(ContentBlock.key == key).first()
    if not block:
        block = ContentBlock(key=key, value=payload.value)
        db.add(block)
    else:
        block.value = payload.value
    db.commit()
    db.refresh(block)
    log_action(db, actor_type="admin", actor_id=admin.id, action="update_content_block", target_type="content", target_id=key, ip_address=_client_ip(request))
    return block


# ---------- Items répétables (listes éditables : étapes, cartes, valeurs, etc.) ----------

@router.get("/items/{group_key}", response_model=list[RepeatableItemOut])
def list_repeatable_items(group_key: str, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Liste TOUS les items d'un groupe (publiés ou non), pour l'écran d'édition admin."""
    return (
        db.query(RepeatableItem)
        .filter(RepeatableItem.group_key == group_key)
        .order_by(RepeatableItem.display_order.asc())
        .all()
    )


@router.post("/items", response_model=RepeatableItemOut, status_code=201)
def create_repeatable_item(payload: RepeatableItemCreate, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["fields"] = json.dumps(data["fields"], ensure_ascii=False)
    item = RepeatableItem(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    log_action(db, actor_type="admin", actor_id=admin.id, action="create_repeatable_item", target_type="repeatable_item", target_id=item.id, details=item.group_key, ip_address=_client_ip(request))
    return item


@router.put("/items/{item_id}", response_model=RepeatableItemOut)
def update_repeatable_item(item_id: str, payload: RepeatableItemUpdate, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    item = db.query(RepeatableItem).filter(RepeatableItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Élément introuvable.")
    updates = payload.model_dump(exclude_unset=True)
    if "fields" in updates and updates["fields"] is not None:
        updates["fields"] = json.dumps(updates["fields"], ensure_ascii=False)
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    log_action(db, actor_type="admin", actor_id=admin.id, action="update_repeatable_item", target_type="repeatable_item", target_id=item.id, details=item.group_key, ip_address=_client_ip(request))
    return item


@router.delete("/items/{item_id}")
def delete_repeatable_item(item_id: str, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    item = db.query(RepeatableItem).filter(RepeatableItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Élément introuvable.")
    group_key = item.group_key
    db.delete(item)
    db.commit()
    log_action(db, actor_type="admin", actor_id=admin.id, action="delete_repeatable_item", target_type="repeatable_item", target_id=item_id, details=group_key, ip_address=_client_ip(request))
    return {"message": "Élément supprimé."}


@router.post("/items/{group_key}/reorder")
def reorder_repeatable_items(group_key: str, payload: RepeatableItemReorder, request: Request, admin: Admin = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Met à jour display_order de tous les items d'un groupe selon l'ordre fourni."""
    items = {item.id: item for item in db.query(RepeatableItem).filter(RepeatableItem.group_key == group_key).all()}
    for index, item_id in enumerate(payload.ordered_ids):
        if item_id in items:
            items[item_id].display_order = index
    db.commit()
    log_action(db, actor_type="admin", actor_id=admin.id, action="reorder_repeatable_items", target_type="repeatable_item", target_id=group_key, ip_address=_client_ip(request))
    return {"message": "Ordre mis à jour."}
