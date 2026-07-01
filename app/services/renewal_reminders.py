"""
Vérification des contrats de maintenance approchant de leur expiration.

PAS de scheduler/cron en arrière-plan (non disponible sur le tier gratuit
Render) : cette vérification est déclenchée à chaque connexion admin
(voir app/routers/auth_admin.py). C'est volontairement "best-effort" — si
l'admin ne se connecte pas pendant plusieurs jours, le rappel sera envoyé
en retard plutôt que jamais, ce qui est acceptable pour ce volume.

Chaque contrat ne reçoit qu'UN SEUL rappel par échéance, grâce à
`renewal_reminder_sent_at` (réinitialisé uniquement si le contrat est
renouvelé / une nouvelle date d'expiration est fixée).
"""
import datetime as dt
import logging

from sqlalchemy.orm import Session

from app.models.maintenance_contract import MaintenanceContract, ContractStatus
from app.services.email_service import send_maintenance_renewal_reminder_email

logger = logging.getLogger("ctq.renewal_reminders")

REMINDER_WINDOW_DAYS = 30


def check_and_send_renewal_reminders(db: Session) -> int:
    """
    Cherche les contrats SIGNED dont l'expiration est dans <= 30 jours et qui
    n'ont pas encore reçu de rappel pour cette échéance, envoie l'email, et
    marque le rappel comme envoyé. Retourne le nombre de rappels envoyés.
    """
    today = dt.date.today()
    threshold = today + dt.timedelta(days=REMINDER_WINDOW_DAYS)

    candidates = (
        db.query(MaintenanceContract)
        .filter(
            MaintenanceContract.status == ContractStatus.SIGNED,
            MaintenanceContract.expiration_date <= threshold,
            MaintenanceContract.renewal_reminder_sent_at.is_(None),
        )
        .all()
    )

    sent_count = 0
    for contract in candidates:
        client = contract.client
        if not client:
            continue
        try:
            send_maintenance_renewal_reminder_email(client, contract)
            contract.renewal_reminder_sent_at = dt.datetime.utcnow()
            db.commit()
            sent_count += 1
        except Exception:
            logger.exception("Échec de l'envoi du rappel de renouvellement pour le contrat %s", contract.contract_number)
            db.rollback()

    return sent_count
