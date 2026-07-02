# ===========================================================
# CYBER TECK Q — Dockerfile
# Image de production pour le service Render (Web Service).
# ===========================================================

FROM python:3.12-slim

# Dépendances système nécessaires à reportlab / pillow (génération PDF) et
# aux polices utilisées dans les factures.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installer les dépendances Python d'abord (meilleure utilisation du cache Docker
# : ce layer n'est reconstruit que si requirements.txt change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code de l'application
COPY app/ ./app/
COPY static_site/ ./static_site/

# Le dossier "data" sera en réalité un point de montage du Render Disk en
# production. On le crée ici pour que l'image fonctionne aussi sans disk
# (ex: tests locaux), mais en production Render écrasera ce dossier vide par
# le volume monté défini dans render.yaml.
RUN mkdir -p /app/data /app/data/uploads

# Render fournit le port d'écoute via la variable d'environnement $PORT.
# On ne fixe pas EXPOSE à une valeur statique pour cette raison.
ENV PYTHONUNBUFFERED=1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
