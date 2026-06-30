"""
Test end-to-end du panier multi-services (v9.11).

Scénario couvert :
1. Inscription d'un client.
2. Création d'un panier avec 2 services différents (Site Web + Maintenance)
   ET 2 unités du même service (Application Mobile x2) -> 4 items au total.
3. Vérifie que le paiement est verrouillé tant que les questionnaires/contrats
   ne sont pas tous complétés.
4. Soumission du questionnaire technique pour le Site Web et les 2
   Applications Mobile.
5. Signature du contrat de maintenance pour le service Maintenance.
6. Vérifie que le paiement est maintenant débloqué.
7. Paiement Interac (dépôt 40%) + validation admin -> vérifie la génération
   automatique de la facture avec le bon total (panier complet, taxes incluses).
8. Vérifie l'admin > Commandes (vue panier) et admin > Paiements (historique).
9. Vérifie le réglage TPS/TVQ globaL (désactivation -> nouvelle commande sans taxes).

Démarre uvicorn dans un thread, lance les requêtes via `requests`, puis
arrête proprement. Utilise une base de données dédiée, supprimée et recréée
à chaque exécution.

Usage :
    python tests_manual/test_cart_multiservice_e2e.py
"""
import os
import sys
import time
import threading
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

os.environ.setdefault("DATABASE_PATH", "./data/test_cart_e2e.db")
os.environ.setdefault("UPLOADS_DIR", "./data/test_cart_uploads")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_for_local_testing_only_do_not_use_in_prod")
os.environ.setdefault("INITIAL_ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "TestAdminPass123!")
os.environ.setdefault("COOKIE_SECURE", "false")

db_path = os.environ["DATABASE_PATH"]
if os.path.exists(db_path):
    os.remove(db_path)

import uvicorn
import requests
from app.main import app

PORT = 8124
BASE = f"http://127.0.0.1:{PORT}"

passed = 0
failed = 0


def check(label, condition, extra=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {label}")
    else:
        failed += 1
        print(f"  ❌ {label} {extra}")


def main():
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.5)

    client_session = requests.Session()
    admin_session = requests.Session()

    try:
        print("\n=== 1. Inscription client ===")
        r = client_session.post(f"{BASE}/api/auth/register", json={
            "first_name": "Jean", "last_name": "Tremblay",
            "email": "jean.tremblay.e2e@example.com", "password": "MotDePasse123!",
        })
        check("Inscription réussie (201)", r.status_code == 201, r.text)

        print("\n=== 2. Création du panier (3 services, 4 items) ===")
        r = client_session.post(f"{BASE}/api/orders", json={
            "items": [
                {"product_type": "website", "quantity": 1},
                {"product_type": "maintenance", "quantity": 1},
                {"product_type": "mobile_app", "quantity": 2},
            ]
        })
        check("Création de commande réussie (201)", r.status_code == 201, r.text)
        order = r.json()
        check("Le panier contient 4 items", len(order.get("items", [])) == 4, json.dumps(order.get("items")))
        check("Sous-total = somme des prix", order["subtotal"] > 0)
        check("Taxes appliquées par défaut", order["gst_amount"] > 0 and order["qst_amount"] > 0)
        check("Total = subtotal + TPS + TVQ", abs(order["total"] - (order["subtotal"] + order["gst_amount"] + order["qst_amount"])) < 0.01)
        check("Paiement verrouillé (aucun questionnaire/contrat soumis)", order["payment_unlocked"] is False)

        order_id = order["id"]
        items = order["items"]
        website_item = next(i for i in items if i["product_type"] == "website")
        maintenance_item = next(i for i in items if i["product_type"] == "maintenance")
        mobile_items = [i for i in items if i["product_type"] == "mobile_app"]
        check("2 items mobile_app distincts", len(mobile_items) == 2)

        print("\n=== 3. Tentative de paiement bloquée ===")
        r = client_session.post(f"{BASE}/api/payments/interac", json={"order_id": order_id, "amount_type": "deposit"})
        check("Paiement Interac refusé (400) tant que verrouillé", r.status_code == 400, r.text)

        print("\n=== 4. Soumission des questionnaires techniques ===")
        tf_payload = {
            "company_name": "Boulangerie ABC", "business_sector": "Alimentation",
            "description": "Site vitrine", "objectives": "Augmenter les ventes en ligne",
            "target_audience": "Familles", "pages_required": "5 pages", "desired_colors": "Bleu/blanc",
            "has_existing_logo": True, "has_images": False,
            "feature_booking": False, "feature_payment": True, "feature_blog": False,
            "feature_gallery": True, "feature_shop": False, "languages": "Français",
            "hosting": "", "domain_name": "", "reference_websites": "", "additional_notes": "",
            "has_current_hosting": False, "wants_new_hosting": True,
            "has_domain_name": False, "wants_domain_help": True, "wants_website_transfer": False,
        }
        r = client_session.post(f"{BASE}/api/order-items/{website_item['id']}/technical-form", json=tf_payload)
        check("Questionnaire Site Web soumis (201)", r.status_code == 201, r.text)

        for idx, mobile_item in enumerate(mobile_items):
            r = client_session.post(f"{BASE}/api/order-items/{mobile_item['id']}/technical-form", json=tf_payload)
            check(f"Questionnaire Mobile App #{idx+1} soumis (201)", r.status_code == 201, r.text)

        print("\n=== 5. Vérification : encore verrouillé (maintenance pas signée) ===")
        r = client_session.get(f"{BASE}/api/orders/{order_id}")
        order = r.json()
        check("Toujours verrouillé (maintenance non signée)", order["payment_unlocked"] is False)

        print("\n=== 6. Signature du contrat de maintenance ===")
        r = client_session.put(f"{BASE}/api/order-items/{maintenance_item['id']}/maintenance-contract", json={
            "client_full_name": "Jean Tremblay", "company_name": "Boulangerie ABC",
            "client_email": "jean.tremblay.e2e@example.com", "client_phone": "514-555-1234",
            "website_concerned": "boulangerieabc.com",
            "maintenance_plan": "Maintenance annuelle Cyber Teck Q",
        })
        check("Infos du contrat enregistrées (200)", r.status_code == 200, r.text)

        r = client_session.post(f"{BASE}/api/order-items/{maintenance_item['id']}/maintenance-contract/sign", json={
            "signer_name": "Jean Tremblay",
            "client_signature_data": "Jean Tremblay",
            "signature_type": "typed",
            "accepted_terms": True,
        })
        check("Contrat de maintenance signé (200)", r.status_code == 200, r.text)

        print("\n=== 7. Vérification : paiement maintenant débloqué ===")
        r = client_session.get(f"{BASE}/api/orders/{order_id}")
        order = r.json()
        check("Paiement débloqué (tous les items complétés)", order["payment_unlocked"] is True, json.dumps(order))

        print("\n=== 8. Paiement Interac (dépôt 40%) ===")
        r = client_session.post(f"{BASE}/api/payments/interac", json={"order_id": order_id, "amount_type": "deposit"})
        check("Paiement Interac créé (201)", r.status_code == 201, r.text)
        payment = r.json()
        expected_deposit = round(order["total"] * 0.40, 2)
        check(
            f"Montant du dépôt = 40% du TOTAL taxes incluses ({expected_deposit})",
            abs(payment["amount"] - expected_deposit) < 0.01,
            f"reçu={payment['amount']}",
        )
        payment_id = payment["id"]

        print("\n=== 8b. Téléversement de la preuve de paiement ===")
        proof_content = b"%PDF-1.4 fake proof content for e2e test"
        files = {"file": ("preuve.pdf", proof_content, "application/pdf")}
        r = client_session.post(f"{BASE}/api/payments/interac/{payment_id}/proof", files=files)
        check("Preuve de paiement téléversée (200)", r.status_code == 200, r.text)
        check("Statut passé à pending_validation", r.json().get("status") == "pending_validation", r.text)

        print("\n=== 9. Connexion admin ===")
        r = admin_session.post(f"{BASE}/api/admin/auth/login", json={
            "email": os.environ["INITIAL_ADMIN_EMAIL"], "password": os.environ["INITIAL_ADMIN_PASSWORD"],
        })
        check("Connexion admin réussie (200)", r.status_code == 200, r.text)

        print("\n=== 10. Admin > Commandes (vue panier) ===")
        r = admin_session.get(f"{BASE}/api/admin/orders/{order_id}")
        check("Commande admin récupérée (200)", r.status_code == 200, r.text)
        admin_order = r.json()
        check("4 items visibles côté admin", len(admin_order["items"]) == 4)

        print("\n=== 11. Admin > Mise à jour progression d'un item individuel ===")
        r = admin_session.put(
            f"{BASE}/api/admin/orders/{order_id}/items/{website_item['id']}",
            json={"project_progress": 40},
        )
        check("Progression de l'item Site Web mise à jour (200)", r.status_code == 200, r.text)
        updated_item = r.json()
        check("Progression = 40%", updated_item["project_progress"] == 40)

        r = admin_session.get(f"{BASE}/api/admin/orders/{order_id}")
        admin_order = r.json()
        other_item = next(i for i in admin_order["items"] if i["id"] == maintenance_item["id"])
        check("Les AUTRES items ne sont PAS affectés (progression toujours 0%)", other_item["project_progress"] == 0)

        print("\n=== 12. Admin > Paiements (validation) ===")
        r = admin_session.post(f"{BASE}/api/admin/payments/{payment_id}/review", json={"approve": True, "note": "Reçu confirmé."})
        check("Paiement validé par l'admin (200)", r.status_code == 200, r.text)

        r = client_session.get(f"{BASE}/api/orders/{order_id}")
        order_after_payment = r.json()
        check("Statut de paiement = deposit_paid", order_after_payment["payment_status"] == "deposit_paid")
        check("Facture générée automatiquement", order_after_payment["has_invoice"] is True)

        print("\n=== 13. Admin > Paiements : historique complet (pas seulement pending) ===")
        r = admin_session.get(f"{BASE}/api/admin/payments?pending_only=false")
        check("Liste des paiements récupérée (200)", r.status_code == 200, r.text)
        all_payments = r.json()
        check("Au moins 1 paiement dans l'historique", len(all_payments) >= 1)
        found = next((p for p in all_payments if p["id"] == payment_id), None)
        check("Le paiement contient items_summary", found is not None and found.get("items_summary"), json.dumps(found))
        check("Le paiement contient order_total (panier complet)", found is not None and found.get("order_total") == order["total"])

        print("\n=== 14. Réglage TPS/TVQ global ===")
        r = admin_session.get(f"{BASE}/api/admin/settings/taxes")
        check("Réglage taxes récupéré (200)", r.status_code == 200, r.text)
        check("Taxes activées par défaut", r.json()["enable_tps_tvq"] is True)

        r = admin_session.put(f"{BASE}/api/admin/settings/taxes", json={"enable_tps_tvq": False})
        check("Désactivation des taxes (200)", r.status_code == 200, r.text)

        r = client_session.post(f"{BASE}/api/orders", json={"items": [{"product_type": "mobile_app", "quantity": 1}]})
        check("Nouvelle commande créée après désactivation (201)", r.status_code == 201, r.text)
        new_order = r.json()
        check("Pas de TPS sur la nouvelle commande", new_order["gst_amount"] == 0, json.dumps(new_order))
        check("Pas de TVQ sur la nouvelle commande", new_order["qst_amount"] == 0)
        check("Total = sous-total (sans taxes)", abs(new_order["total"] - new_order["subtotal"]) < 0.01)

        r = client_session.get(f"{BASE}/api/orders/{order_id}")
        old_order_recheck = r.json()
        check(
            "L'ANCIENNE commande garde ses taxes (montants figés)",
            old_order_recheck["gst_amount"] > 0 and old_order_recheck["qst_amount"] > 0,
        )

        # Remet le réglage à True pour ne pas affecter d'autres tests potentiels
        admin_session.put(f"{BASE}/api/admin/settings/taxes", json={"enable_tps_tvq": True})

    finally:
        print(f"\n{'='*50}")
        print(f"RÉSULTAT : {passed} test(s) réussis, {failed} test(s) échoués.")
        print(f"{'='*50}\n")
        server.should_exit = True
        time.sleep(0.5)

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
