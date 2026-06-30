"""Router : CMS public (FAQ, tarifs, blocs de contenu visibles par tous)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.content import FaqEntry, PricingPlan, ContentBlock, RepeatableItem
from app.schemas.cms_schemas import FaqEntryOut, PricingPlanOut, ContentBlockOut, RepeatableItemOut

router = APIRouter(prefix="/api/cms", tags=["cms-public"])


@router.get("/items", response_model=dict[str, list[RepeatableItemOut]])
def get_public_repeatable_items_bulk(groups: str, db: Session = Depends(get_db)):
    """
    Retourne les items publiés de plusieurs groupes en une seule requête.
    `groups` est une liste de group_key séparés par des virgules, ex:
    '?groups=home.story.steps,home.mission.values,home.trust_items'
    """
    keys = [g.strip() for g in groups.split(",") if g.strip()]
    result: dict[str, list] = {k: [] for k in keys}
    if not keys:
        return result
    items = (
        db.query(RepeatableItem)
        .filter(RepeatableItem.group_key.in_(keys), RepeatableItem.is_published == True)  # noqa: E712
        .order_by(RepeatableItem.group_key.asc(), RepeatableItem.display_order.asc())
        .all()
    )
    for item in items:
        result.setdefault(item.group_key, []).append(item)
    return result


@router.get("/items/{group_key}", response_model=list[RepeatableItemOut])
def get_public_repeatable_items(group_key: str, db: Session = Depends(get_db)):
    """Retourne les items publiés d'un groupe (ex: 'home.story.steps'), triés pour affichage."""
    return (
        db.query(RepeatableItem)
        .filter(RepeatableItem.group_key == group_key, RepeatableItem.is_published == True)  # noqa: E712
        .order_by(RepeatableItem.display_order.asc())
        .all()
    )


@router.get("/faq", response_model=list[FaqEntryOut])
def get_public_faq(db: Session = Depends(get_db)):
    return (
        db.query(FaqEntry)
        .filter(FaqEntry.is_published == True)  # noqa: E712
        .order_by(FaqEntry.display_order.asc())
        .all()
    )


@router.get("/pricing", response_model=list[PricingPlanOut])
def get_public_pricing(db: Session = Depends(get_db)):
    return (
        db.query(PricingPlan)
        .filter(PricingPlan.is_published == True)  # noqa: E712
        .order_by(PricingPlan.display_order.asc())
        .all()
    )


@router.get("/content", response_model=list[ContentBlockOut])
def list_all_content_blocks(db: Session = Depends(get_db)):
    """Retourne tous les blocs de contenu (utile pour charger le footer/coordonnées en un seul appel)."""
    return db.query(ContentBlock).all()


@router.get("/content/{key}", response_model=ContentBlockOut)
def get_content_block(key: str, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    block = db.query(ContentBlock).filter(ContentBlock.key == key).first()
    if not block:
        raise HTTPException(status_code=404, detail="Bloc de contenu introuvable.")
    return block
