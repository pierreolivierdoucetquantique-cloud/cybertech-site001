"""
Migration v9.11 : panier multi-services (Order devient un panier, OrderItem
représente chaque service individuel).

CE QUE FAIT CETTE MIGRATION :
1. Ajoute les nouvelles colonnes de montants (subtotal, taxes_applied,
   gst_amount, qst_amount, total) à la table `orders` existante.
2. Crée la nouvelle table `order_items`.
3. Pour CHAQUE Order existante : crée UN OrderItem qui copie product_type,
   product_name, price, project_progress, expected_delivery_date — puis
   copie les montants de taxes déjà calculés (depuis la facture existante
   si elle existe, sinon recalculés à partir de l'ancien `price`).
4. Migre `technical_forms.order_id` → `technical_forms.order_item_id` en
   recréant la table (SQLite ne permet pas de modifier une FK existante
   directement) et en pointant chaque ligne vers le bon OrderItem créé à
   l'étape 3.
5. Fait la même chose pour `maintenance_contracts.order_id` →
   `maintenance_contracts.order_item_id`, et ajoute la colonne
   `renewal_reminder_sent_at`.
6. Ajoute les nouvelles colonnes liées au remboursement et aux infos de
   carte sur `payments` (card_brand, card_last4, refunded_amount,
   refund_reason, refunded_at, stripe_refund_id) — sans cette étape, la
   page Admin > Paiements plante avec une erreur 500 sur une base existante
   (colonne manquante), même si tout le reste de la migration a réussi.
7. Supprime les anciennes colonnes `product_type`, `product_name`, `price`,
   `project_progress`, `expected_delivery_date` de `orders` (elles vivent
   maintenant sur `order_items`) en recréant la table `orders`.

SÉCURITÉ :
- Tout se déroule dans UNE SEULE transaction SQLite (BEGIN ... COMMIT).
  Si une étape échoue, TOUT est annulé (ROLLBACK) — aucune donnée n'est
  perdue ou laissée dans un état intermédiaire incohérent.
- Idempotente : si `order_items` existe déjà ET contient au moins une ligne
  par Order existante, le script se termine sans rien faire.
- Fait une COPIE DE SAUVEGARDE du fichier .db avant de commencer (à côté du
  fichier original, avec un horodatage), au cas où une vérification manuelle
  serait nécessaire après coup.

USAGE (à exécuter UNE SEULE FOIS après le déploiement de la v9.11, via le
Shell Render, ou en local en pointant DATABASE_PATH vers une copie du
fichier .db) :

    python tests_manual/migrate_v9_11_cart_order_items.py
    python tests_manual/migrate_v9_11_cart_order_items.py /chemin/vers/cyberteckq.db
"""
import os
import shutil
import sqlite3
import sys
import uuid
import datetime as dt

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DATABASE_PATH", "./data/cyberteckq.db")

TAX_RATE_GST = 0.05
TAX_RATE_QST = 0.09975


def gen_uuid() -> str:
    return str(uuid.uuid4())


def column_exists(cur, table: str, column: str) -> bool:
    cur.execute(f"PRAGMA table_info({table});")
    return column in {row[1] for row in cur.fetchall()}


def table_exists(cur, table: str) -> bool:
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
    return cur.fetchone() is not None


def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Fichier de base de données introuvable : {DB_PATH}")
        print("   Précisez le chemin en argument : python migrate_v9_11_cart_order_items.py /chemin/vers/cyberteckq.db")
        sys.exit(1)

    # --- Sauvegarde de sécurité avant toute modification ---
    backup_path = f"{DB_PATH}.before-v9.11-{dt.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.bak"
    shutil.copy2(DB_PATH, backup_path)
    print(f"💾 Sauvegarde créée : {backup_path}")

    print(f"📂 Connexion à : {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF;")  # désactivé pendant la recréation de tables
    cur = conn.cursor()

    # --- Vérification d'idempotence ---
    if table_exists(cur, "order_items"):
        cur.execute("SELECT COUNT(*) FROM order_items;")
        items_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM orders;")
        orders_count = cur.fetchone()[0]
        if items_count >= orders_count and not column_exists(cur, "orders", "product_type"):
            print("✔️  Migration déjà appliquée (order_items existe, orders est déjà au nouveau format). Rien à faire.")
            conn.close()
            return

    try:
        cur.execute("BEGIN;")

        # ============================================================
        # ÉTAPE 1 : nouvelles colonnes de montants sur `orders`
        # ============================================================
        for col_name, col_type, default in [
            ("subtotal", "FLOAT", "0.0"),
            ("taxes_applied", "VARCHAR", "'true'"),
            ("gst_amount", "FLOAT", "0.0"),
            ("qst_amount", "FLOAT", "0.0"),
            ("total", "FLOAT", "0.0"),
        ]:
            if not column_exists(cur, "orders", col_name):
                cur.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type} DEFAULT {default};")
                print(f"✅ Colonne ajoutée sur orders : {col_name}")

        # ============================================================
        # ÉTAPE 2 : créer order_items si elle n'existe pas
        # ============================================================
        if not table_exists(cur, "order_items"):
            cur.execute("""
                CREATE TABLE order_items (
                    id VARCHAR PRIMARY KEY,
                    order_id VARCHAR NOT NULL,
                    product_type VARCHAR NOT NULL,
                    product_name VARCHAR NOT NULL,
                    price FLOAT NOT NULL,
                    project_progress INTEGER DEFAULT 0,
                    expected_delivery_date DATE,
                    created_at DATETIME,
                    updated_at DATETIME,
                    FOREIGN KEY(order_id) REFERENCES orders(id)
                );
            """)
            cur.execute("CREATE INDEX ix_order_items_order_id ON order_items (order_id);")
            print("✅ Table order_items créée.")

        # ============================================================
        # ÉTAPE 3 : un OrderItem par Order existante (si pas déjà fait),
        # avec une facture existante si présente pour récupérer les
        # montants de taxes déjà émis (sinon on les recalcule).
        # ============================================================
        has_invoices_table = table_exists(cur, "invoices")
        old_order_has_product_cols = column_exists(cur, "orders", "product_type")

        if old_order_has_product_cols:
            cur.execute("""
                SELECT id, product_type, product_name, price, project_progress,
                       expected_delivery_date, created_at, updated_at
                FROM orders;
            """)
            old_orders = cur.fetchall()

            migrated_items = 0
            order_item_id_by_order = {}

            for (order_id, product_type, product_name, price, progress,
                 delivery_date, created_at, updated_at) in old_orders:

                cur.execute("SELECT COUNT(*) FROM order_items WHERE order_id = ?;", (order_id,))
                if cur.fetchone()[0] > 0:
                    cur.execute("SELECT id FROM order_items WHERE order_id = ? LIMIT 1;", (order_id,))
                    order_item_id_by_order[order_id] = cur.fetchone()[0]
                    continue  # déjà migré pour cette commande

                item_id = gen_uuid()
                cur.execute("""
                    INSERT INTO order_items
                        (id, order_id, product_type, product_name, price,
                         project_progress, expected_delivery_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (item_id, order_id, product_type, product_name, price or 0.0,
                      progress or 0, delivery_date, created_at, updated_at))
                order_item_id_by_order[order_id] = item_id
                migrated_items += 1

                # Calcule/copie subtotal, taxes, total sur la commande elle-même
                gst_amount, qst_amount, total = None, None, None
                if has_invoices_table:
                    cur.execute("SELECT subtotal, gst_amount, qst_amount, total FROM invoices WHERE order_id = ?;", (order_id,))
                    inv = cur.fetchone()
                    if inv:
                        _, gst_amount, qst_amount, total = inv

                subtotal = price or 0.0
                if gst_amount is None:
                    gst_amount = round(subtotal * TAX_RATE_GST, 2)
                    qst_amount = round(subtotal * TAX_RATE_QST, 2)
                    total = round(subtotal + gst_amount + qst_amount, 2)

                cur.execute("""
                    UPDATE orders
                    SET subtotal = ?, taxes_applied = 'true', gst_amount = ?, qst_amount = ?, total = ?
                    WHERE id = ?;
                """, (subtotal, gst_amount, qst_amount, total, order_id))

            print(f"✅ {migrated_items} OrderItem créé(s) à partir des commandes existantes.")
        else:
            # orders est déjà au nouveau format (pas de colonne product_type) :
            # on construit juste la table de correspondance order_id -> order_item_id
            # à partir de order_items déjà peuplée (utile si le script est relancé
            # après une exécution partielle).
            cur.execute("SELECT order_id, id FROM order_items;")
            order_item_id_by_order = {}
            for order_id, item_id in cur.fetchall():
                order_item_id_by_order.setdefault(order_id, item_id)

        # ============================================================
        # ÉTAPE 4 : migrer technical_forms.order_id -> order_item_id
        # ============================================================
        if column_exists(cur, "technical_forms", "order_id"):
            cur.execute("""
                CREATE TABLE technical_forms_new (
                    id VARCHAR PRIMARY KEY,
                    order_item_id VARCHAR NOT NULL UNIQUE,
                    client_id VARCHAR NOT NULL,
                    company_name VARCHAR, business_sector VARCHAR, description TEXT,
                    objectives TEXT, target_audience TEXT, pages_required TEXT,
                    desired_colors VARCHAR, has_existing_logo BOOLEAN, has_images BOOLEAN,
                    feature_booking BOOLEAN, feature_payment BOOLEAN, feature_blog BOOLEAN,
                    feature_gallery BOOLEAN, feature_shop BOOLEAN, languages VARCHAR,
                    hosting VARCHAR, domain_name VARCHAR, reference_websites TEXT,
                    additional_notes TEXT,
                    has_current_hosting BOOLEAN, hosting_provider VARCHAR,
                    hosting_access_details TEXT, wants_new_hosting BOOLEAN,
                    has_domain_name BOOLEAN, wants_domain_help BOOLEAN,
                    wants_website_transfer BOOLEAN,
                    submitted_at DATETIME,
                    FOREIGN KEY(order_item_id) REFERENCES order_items(id)
                );
            """)
            cur.execute("SELECT * FROM technical_forms;")
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            skipped = 0
            for row in rows:
                data = dict(zip(cols, row))
                old_order_id = data.pop("order_id")
                new_item_id = order_item_id_by_order.get(old_order_id)
                if not new_item_id:
                    skipped += 1
                    continue
                data["order_item_id"] = new_item_id
                placeholders = ", ".join("?" for _ in data)
                cur.execute(
                    f"INSERT INTO technical_forms_new ({', '.join(data.keys())}) VALUES ({placeholders});",
                    list(data.values()),
                )
            cur.execute("DROP TABLE technical_forms;")
            cur.execute("ALTER TABLE technical_forms_new RENAME TO technical_forms;")
            print(f"✅ technical_forms migrée vers order_item_id ({len(rows) - skipped} ligne(s), {skipped} ignorée(s) si orpheline(s)).")

        # ============================================================
        # ÉTAPE 5 : migrer maintenance_contracts.order_id -> order_item_id
        #           + ajouter renewal_reminder_sent_at
        # ============================================================
        if column_exists(cur, "maintenance_contracts", "order_id"):
            cur.execute("""
                CREATE TABLE maintenance_contracts_new (
                    id VARCHAR PRIMARY KEY,
                    contract_number VARCHAR NOT NULL UNIQUE,
                    order_item_id VARCHAR NOT NULL UNIQUE,
                    client_id VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    client_full_name VARCHAR NOT NULL, company_name VARCHAR,
                    client_email VARCHAR NOT NULL, client_phone VARCHAR,
                    website_concerned VARCHAR,
                    maintenance_plan VARCHAR NOT NULL, annual_price FLOAT NOT NULL,
                    contract_duration_months INTEGER NOT NULL,
                    effective_date DATE NOT NULL, expiration_date DATE NOT NULL,
                    signer_name VARCHAR, client_signature_data TEXT,
                    signature_type VARCHAR, accepted_terms BOOLEAN,
                    signed_at DATETIME, signed_ip_address VARCHAR,
                    admin_signature_name VARCHAR, admin_signed_at DATETIME,
                    pdf_path VARCHAR,
                    renewal_reminder_sent_at DATETIME,
                    created_at DATETIME, updated_at DATETIME,
                    FOREIGN KEY(order_item_id) REFERENCES order_items(id)
                );
            """)
            cur.execute("SELECT * FROM maintenance_contracts;")
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            skipped = 0
            for row in rows:
                data = dict(zip(cols, row))
                old_order_id = data.pop("order_id")
                new_item_id = order_item_id_by_order.get(old_order_id)
                if not new_item_id:
                    skipped += 1
                    continue
                data["order_item_id"] = new_item_id
                data.setdefault("renewal_reminder_sent_at", None)
                placeholders = ", ".join("?" for _ in data)
                cur.execute(
                    f"INSERT INTO maintenance_contracts_new ({', '.join(data.keys())}) VALUES ({placeholders});",
                    list(data.values()),
                )
            cur.execute("DROP TABLE maintenance_contracts;")
            cur.execute("ALTER TABLE maintenance_contracts_new RENAME TO maintenance_contracts;")
            print(f"✅ maintenance_contracts migrée vers order_item_id ({len(rows) - skipped} ligne(s), {skipped} ignorée(s) si orpheline(s)).")
        elif not column_exists(cur, "maintenance_contracts", "renewal_reminder_sent_at"):
            cur.execute("ALTER TABLE maintenance_contracts ADD COLUMN renewal_reminder_sent_at DATETIME;")
            print("✅ Colonne renewal_reminder_sent_at ajoutée sur maintenance_contracts.")

        # ============================================================
        # ÉTAPE 6 : nouvelles colonnes sur `payments` (remboursement, carte)
        # ============================================================
        for col_name, col_type in [
            ("card_brand", "VARCHAR"),
            ("card_last4", "VARCHAR"),
            ("refunded_amount", "FLOAT"),
            ("refund_reason", "TEXT"),
            ("refunded_at", "DATETIME"),
            ("stripe_refund_id", "VARCHAR"),
        ]:
            if not column_exists(cur, "payments", col_name):
                cur.execute(f"ALTER TABLE payments ADD COLUMN {col_name} {col_type};")
                print(f"✅ Colonne ajoutée sur payments : {col_name}")

        # ============================================================
        # ÉTAPE 7 : retirer les anciennes colonnes produit de `orders`
        #           (recréation de table, pattern standard SQLite)
        # ============================================================
        if column_exists(cur, "orders", "product_type"):
            cur.execute("""
                CREATE TABLE orders_new (
                    id VARCHAR PRIMARY KEY,
                    order_number VARCHAR NOT NULL UNIQUE,
                    client_id VARCHAR NOT NULL,
                    subtotal FLOAT NOT NULL DEFAULT 0.0,
                    taxes_applied VARCHAR NOT NULL DEFAULT 'true',
                    gst_amount FLOAT NOT NULL DEFAULT 0.0,
                    qst_amount FLOAT NOT NULL DEFAULT 0.0,
                    total FLOAT NOT NULL DEFAULT 0.0,
                    status VARCHAR, payment_status VARCHAR,
                    notes TEXT,
                    created_at DATETIME, updated_at DATETIME
                );
            """)
            cur.execute("""
                INSERT INTO orders_new
                    (id, order_number, client_id, subtotal, taxes_applied,
                     gst_amount, qst_amount, total, status, payment_status,
                     notes, created_at, updated_at)
                SELECT id, order_number, client_id, subtotal, taxes_applied,
                       gst_amount, qst_amount, total, status, payment_status,
                       notes, created_at, updated_at
                FROM orders;
            """)
            cur.execute("DROP TABLE orders;")
            cur.execute("ALTER TABLE orders_new RENAME TO orders;")
            cur.execute("CREATE UNIQUE INDEX ix_orders_order_number ON orders (order_number);")
            print("✅ Table orders nettoyée (anciennes colonnes produit retirées).")

        cur.execute("COMMIT;")
        conn.execute("PRAGMA foreign_keys = ON;")
        print("\n🎉 Migration v9.11 terminée avec succès.")
        print(f"   (Sauvegarde conservée au cas où : {backup_path})")

    except Exception as exc:
        cur.execute("ROLLBACK;")
        print(f"\n❌ ERREUR pendant la migration — TOUT a été annulé (rollback) : {exc}")
        print(f"   Aucune donnée n'a été modifiée. La sauvegarde reste disponible : {backup_path}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
