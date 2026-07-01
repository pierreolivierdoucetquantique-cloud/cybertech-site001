"""
Service de réglages globaux de la plateforme, stockés comme ContentBlock
(clé/valeur) pour éviter de créer une table dédiée pour un seul interrupteur.

Réglage actuel :
- ENABLE_TPS_TVQ : active/désactive le calcul de la TPS et de la TVQ sur
  TOUTES les nouvelles commandes/factures. Ne touche jamais les commandes
  déjà créées (leurs montants sont figés au moment de la création, comme une
  facture émise).
"""
from sqlalchemy.orm import Session

from app.models.content import ContentBlock

TAXES_SETTING_KEY = "admin.settings.enable_tps_tvq"


def is_taxes_enabled(db: Session) -> bool:
    """Retourne True si TPS/TVQ doivent être appliquées (réglage par défaut : activé)."""
    block = db.query(ContentBlock).filter(ContentBlock.key == TAXES_SETTING_KEY).first()
    if block is None:
        return True  # comportement historique : taxes toujours appliquées par défaut
    return block.value == "true"


def set_taxes_enabled(db: Session, enabled: bool) -> bool:
    block = db.query(ContentBlock).filter(ContentBlock.key == TAXES_SETTING_KEY).first()
    if block is None:
        block = ContentBlock(
            key=TAXES_SETTING_KEY,
            label="Appliquer TPS (5%) et TVQ (9.975%) sur les nouvelles commandes",
            value="true" if enabled else "false",
            content_type="boolean",
        )
        db.add(block)
    else:
        block.value = "true" if enabled else "false"
    db.commit()
    return enabled
