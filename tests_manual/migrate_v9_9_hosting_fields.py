"""
Migration v9.9 : ajoute les colonnes de la section "Hébergement Web" à la table
technical_forms. Sans cette migration, le serveur plantera (sqlite3.OperationalError:
no such column) dès qu'une route lira/écrira ces colonnes sur une DB existante,
car Base.metadata.create_all() ne fait jamais d'ALTER TABLE sur une table déjà créée.

Idempotent : peut être lancé plusieurs fois sans risque (vérifie d'abord les
colonnes existantes avant chaque ALTER TABLE).

Usage (à exécuter une seule fois après le déploiement de la v9.9, via le Shell
Render ou en local en pointant DATABASE_PATH vers une copie du fichier .db) :

    python tests_manual/migrate_v9_9_hosting_fields.py
"""
import os
import sqlite3
import sys

# Permet de surcharger le chemin de la DB via variable d'environnement ou argument CLI
DB_PATH = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DATABASE_PATH", "./data/cyberteckq.db")

NEW_COLUMNS = [
    ("has_current_hosting", "BOOLEAN"),
    ("hosting_provider", "VARCHAR"),
    ("hosting_access_details", "TEXT"),
    ("wants_new_hosting", "BOOLEAN"),
    ("has_domain_name", "BOOLEAN"),
    ("wants_domain_help", "BOOLEAN"),
    ("wants_website_transfer", "BOOLEAN"),
]


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Fichier de base de données introuvable : {DB_PATH}")
        print("   Précisez le chemin en argument : python migrate_v9_9_hosting_fields.py /chemin/vers/cyberteckq.db")
        sys.exit(1)

    print(f"📂 Connexion à : {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(technical_forms);")
    existing_columns = {row[1] for row in cur.fetchall()}

    added = []
    for col_name, col_type in NEW_COLUMNS:
        if col_name in existing_columns:
            print(f"⏭️  Colonne déjà présente, ignorée : {col_name}")
            continue
        cur.execute(f"ALTER TABLE technical_forms ADD COLUMN {col_name} {col_type};")
        added.append(col_name)
        print(f"✅ Colonne ajoutée : {col_name} ({col_type})")

    conn.commit()
    conn.close()

    if added:
        print(f"\n🎉 Migration terminée. {len(added)} colonne(s) ajoutée(s).")
    else:
        print("\n✔️  Rien à faire, la table était déjà à jour.")


if __name__ == "__main__":
    main()
