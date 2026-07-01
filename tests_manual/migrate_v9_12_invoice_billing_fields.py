"""
Migration v9.12 : ajoute les colonnes de facturation automatique (dépôt 40% /
paiement complet) à la table invoices : deposit_amount, amount_paid,
remaining_balance, status, updated_at.

Sans cette migration, le serveur plantera (sqlite3.OperationalError: no such
column) dès qu'une route lira/écrira ces colonnes sur une DB existante, car
Base.metadata.create_all() ne fait jamais d'ALTER TABLE sur une table déjà créée.

Rétro-remplissage (backfill) : pour chaque facture existante, les nouvelles
colonnes sont déduites du payment_status de la commande liée (source de
vérité déjà en place avant cette migration) — la prochaine synchronisation
réelle (nouveau paiement) recalculera ensuite tout automatiquement et
régénérera le PDF avec les montants exacts.

Idempotent : peut être lancé plusieurs fois sans risque (vérifie d'abord les
colonnes existantes avant chaque ALTER TABLE ; le backfill ne touche que les
lignes où status est encore NULL).

Usage (à exécuter une seule fois après le déploiement de la v9.12, via le
Shell Render ou en local en pointant DATABASE_PATH vers une copie du fichier
.db) :

    python tests_manual/migrate_v9_12_invoice_billing_fields.py
"""
import os
import sqlite3
import sys

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DATABASE_PATH", "./data/cyberteckq.db")

NEW_COLUMNS = [
    ("deposit_amount", "REAL"),
    ("amount_paid", "REAL DEFAULT 0"),
    ("remaining_balance", "REAL DEFAULT 0"),
    ("status", "VARCHAR"),
    ("updated_at", "DATETIME"),
]

DEPOSIT_PERCENTAGE = 0.40


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Fichier de base de données introuvable : {DB_PATH}")
        print("   Précisez le chemin en argument : python migrate_v9_12_invoice_billing_fields.py /chemin/vers/cyberteckq.db")
        sys.exit(1)

    print(f"📂 Connexion à : {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(invoices);")
    existing_columns = {row[1] for row in cur.fetchall()}

    added = []
    for col_name, col_type in NEW_COLUMNS:
        if col_name in existing_columns:
            print(f"⏭️  Colonne déjà présente, ignorée : {col_name}")
            continue
        cur.execute(f"ALTER TABLE invoices ADD COLUMN {col_name} {col_type};")
        added.append(col_name)
        print(f"✅ Colonne ajoutée : {col_name} ({col_type})")

    conn.commit()

    # --- Rétro-remplissage des factures existantes ---
    cur.execute("""
        SELECT invoices.id, invoices.total, orders.payment_status, orders.total
        FROM invoices
        JOIN orders ON orders.id = invoices.order_id
        WHERE invoices.status IS NULL;
    """)
    rows = cur.fetchall()

    backfilled = 0
    for invoice_id, invoice_total, order_payment_status, order_total in rows:
        total = order_total if order_total else invoice_total

        if order_payment_status == "paid":
            status, deposit_amount, amount_paid, remaining = "Paid in Full", None, total, 0.0
        elif order_payment_status == "deposit_paid":
            deposit_amount = round(total * DEPOSIT_PERCENTAGE, 2)
            status, amount_paid, remaining = "Deposit Paid", deposit_amount, round(total - deposit_amount, 2)
        elif order_payment_status == "refunded":
            status, deposit_amount, amount_paid, remaining = "Refunded", None, 0.0, 0.0
        elif order_payment_status == "partially_refunded":
            deposit_amount = round(total * DEPOSIT_PERCENTAGE, 2)
            status, amount_paid, remaining = "Partially Refunded", deposit_amount, round(total - deposit_amount, 2)
        else:
            # État imprévu (ex: facture orpheline) — traité prudemment comme dépôt payé.
            deposit_amount = round(total * DEPOSIT_PERCENTAGE, 2)
            status, amount_paid, remaining = "Deposit Paid", deposit_amount, round(total - deposit_amount, 2)

        cur.execute(
            "UPDATE invoices SET status = ?, deposit_amount = ?, amount_paid = ?, remaining_balance = ?, updated_at = datetime('now') WHERE id = ?;",
            (status, deposit_amount, amount_paid, remaining, invoice_id),
        )
        backfilled += 1

    conn.commit()
    conn.close()

    if added:
        print(f"\n🎉 Migration terminée. {len(added)} colonne(s) ajoutée(s), {backfilled} facture(s) rétro-remplie(s).")
    elif backfilled:
        print(f"\n🎉 Rétro-remplissage terminé pour {backfilled} facture(s).")
    else:
        print("\n✔️  Rien à faire, la table était déjà à jour.")

    print(
        "\nℹ️  Les montants rétro-remplis sont des ESTIMATIONS basées sur le statut "
        "de paiement de la commande. Le prochain paiement confirmé (ou un renvoi "
        "manuel de facture) recalculera automatiquement les valeurs exactes et "
        "régénérera le PDF."
    )


if __name__ == "__main__":
    main()
