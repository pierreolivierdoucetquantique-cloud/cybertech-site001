"""
Bootstrap du compte administrateur initial.

Au démarrage du serveur, si AUCUN admin n'existe en base ET que les variables
d'environnement INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD sont définies,
un premier compte admin est créé automatiquement. C'est la SEULE façon
d'obtenir un premier accès — il n'existe aucune route publique de création
d'admin (ce serait une faille de sécurité majeure).

En production (Render), définir ces deux variables d'environnement, démarrer
le service une première fois, puis (optionnellement) les retirer du dashboard
Render une fois le compte créé.
"""
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models.admin import Admin
from app.utils.security import hash_password

logger = logging.getLogger("ctq.bootstrap")


def bootstrap_initial_admin(db: Session) -> None:
    existing_count = db.query(Admin).count()
    if existing_count > 0:
        return

    if not settings.INITIAL_ADMIN_EMAIL or not settings.INITIAL_ADMIN_PASSWORD:
        logger.warning(
            "Aucun compte admin n'existe et INITIAL_ADMIN_EMAIL/INITIAL_ADMIN_PASSWORD "
            "ne sont pas configurés. Définissez ces variables d'environnement et "
            "redémarrez le serveur pour créer le premier accès admin."
        )
        return

    if len(settings.INITIAL_ADMIN_PASSWORD) < 8:
        logger.error("INITIAL_ADMIN_PASSWORD est trop court (minimum 8 caractères) — admin non créé.")
        return

    admin = Admin(
        email=settings.INITIAL_ADMIN_EMAIL.lower(),
        password_hash=hash_password(settings.INITIAL_ADMIN_PASSWORD),
        full_name="Administrateur",
        role="admin",
    )
    db.add(admin)
    db.commit()
    logger.info("Compte admin initial créé pour %s", settings.INITIAL_ADMIN_EMAIL)
