"""Service d'enregistrement des actions sensibles dans le journal d'audit."""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.admin import AuditLog


def log_action(
    db: Session,
    actor_type: str,
    action: str,
    actor_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    entry = AuditLog(
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
