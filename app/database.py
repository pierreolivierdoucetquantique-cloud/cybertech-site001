"""
Connexion à la base de données SQLite via SQLAlchemy.
Le fichier .db vit sur le Render Disk (chemin configuré via DATABASE_PATH).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# S'assurer que le dossier parent existe (utile en local ET sur le disk Render)
db_dir = os.path.dirname(settings.DATABASE_PATH)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

os.makedirs(settings.UPLOADS_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{settings.DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # nécessaire pour SQLite + FastAPI
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency FastAPI : fournit une session DB et la ferme proprement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Crée toutes les tables si elles n'existent pas déjà."""
    # Importer tous les modèles ici pour qu'ils soient enregistrés sur Base
    from app.models import client, order, invoice, project, technical_form, admin, content, contact_message, upload, payment, maintenance_contract  # noqa
    Base.metadata.create_all(bind=engine)
