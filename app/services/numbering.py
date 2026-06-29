"""
Génération de numéros séquentiels (commandes, factures) garantis sans
doublon, même en cas de requêtes concurrentes.

Stratégie : la ligne "compteur" est verrouillée (SELECT ... FOR UPDATE-style
via une transaction SQLite immédiate) pendant l'incrémentation, ce qui sérialise
les accès. SQLite gère nativement l'écriture séquentielle d'une base unique,
donc ce verrou applicatif suffit pour notre volume (une seule instance Render).
"""
import datetime as dt
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.order import OrderCounter
from app.models.invoice import InvoiceCounter
from app.models.maintenance_contract import MaintenanceContractCounter
from app.config import settings


def _next_number(db: Session, counter_model, prefix: str) -> str:
    current_year = dt.datetime.utcnow().year
    year_suffix = str(current_year)[-2:]  # ex: 2026 -> "26"

    # Démarre une transaction explicite et verrouille la ligne du compteur.
    # BEGIN IMMEDIATE empêche toute autre écriture concurrente sur la DB
    # jusqu'au commit, ce qui élimine les conditions de course sur SQLite.
    db.execute(text("BEGIN IMMEDIATE"))
    try:
        counter = (
            db.query(counter_model)
            .filter(counter_model.id == "singleton")
            .first()
        )
        if counter is None:
            counter = counter_model(id="singleton", last_number=0, year=current_year)
            db.add(counter)
            db.flush()

        # Si on change d'année, on repart à 1 (numérotation par année)
        if counter.year != current_year:
            counter.year = current_year
            counter.last_number = 0

        counter.last_number += 1
        next_num = counter.last_number
        db.commit()
    except Exception:
        db.rollback()
        raise

    return f"{prefix}-{year_suffix}-{next_num:05d}"


def next_order_number(db: Session) -> str:
    return _next_number(db, OrderCounter, "ORD")


def next_invoice_number(db: Session) -> str:
    return _next_number(db, InvoiceCounter, settings.INVOICE_PREFIX)


def next_maintenance_contract_number(db: Session) -> str:
    return _next_number(db, MaintenanceContractCounter, f"{settings.INVOICE_PREFIX}-MNT")
