"""
Test end-to-end du module Contrat de Maintenance (v9.10).

Démarre uvicorn dans un thread, lance les requêtes via `requests`, puis
arrête proprement — évite les soucis de process détaché entre appels d'outils.
Utilise une base de données dédiée (./data/test_maintenance_e2e.db),
supprimée et recréée à chaque exécution.

Usage :
    python tests_manual/test_maintenance_e2e.py
"""
import os
import sys
import time
import threading
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

# Configuration minimale pour un environnement de test isolé, sans dépendre
# d'un fichier .env externe.
os.environ.setdefault("DATABASE_PATH", "./data/test_maintenance_e2e.db")
os.environ.setdefault("UPLOADS_DIR", "./data/test_uploads")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_for_local_testing_only_do_not_use_in_prod")
os.environ.setdefault("INITIAL_ADMIN_EMAIL", "admin@example.com")
os.environ.setdefault("INITIAL_ADMIN_PASSWORD", "TestAdminPass123!")
os.environ.setdefault("COOKIE_SECURE", "false")

db_path = os.environ["DATABASE_PATH"]
if os.path.exists(db_path):
    os.remove(db_path)

import uvicorn
from app.main import app

PORT = 8123
BASE = f"http://127.0.0.1:{PORT}"

server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning"))

def run_server():
    server.run()

thread = threading.Thread(target=run_server, daemon=True)
thread.start()

# Attendre que le serveur soit prêt
for _ in range(50):
    if getattr(server, "started", False):
        break
    time.sleep(0.1)
time.sleep(0.5)

import requests

session = requests.Session()
errors = []

def check(label, condition, extra=""):
    status = "OK" if condition else "FAIL"
    print(f"[{status}] {label} {extra}")
    if not condition:
        errors.append(label)


print("=== 1. Health check ===")
r = session.get(f"{BASE}/api/health")
check("health 200", r.status_code == 200, r.text)

print("=== 2. Register client ===")
r = session.post(f"{BASE}/api/auth/register", json={
    "first_name": "Jean", "last_name": "Tremblay",
    "email": "jean.tremblay@example.com", "password": "MotDePasse123!",
    "phone": "418-555-0123",
})
check("register 201", r.status_code == 201, f"{r.status_code} {r.text}")

print("=== 3. Create MAINTENANCE order ===")
r = session.post(f"{BASE}/api/orders", json={"product_type": "maintenance"})
check("create order 201", r.status_code == 201, f"{r.status_code} {r.text}")
order = r.json()
order_id = order.get("id")
print("order:", json.dumps(order, indent=2, default=str))
check("has_maintenance_contract False at creation", order.get("has_maintenance_contract") is False)
check("payment_unlocked False at creation", order.get("payment_unlocked") is False)

print("=== 4. Attempt Stripe checkout BEFORE contract signed -> must fail ===")
r = session.post(f"{BASE}/api/payments/stripe/checkout", json={"order_id": order_id, "amount_type": "deposit"})
check("payment blocked before signature (400)", r.status_code == 400, f"{r.status_code} {r.text}")

print("=== 5. Attempt to submit technical-form on a MAINTENANCE order -> must fail ===")
r = session.post(f"{BASE}/api/orders/{order_id}/technical-form", json={"company_name": "Test"})
check("technical-form blocked on maintenance order (400)", r.status_code == 400, f"{r.status_code} {r.text}")

print("=== 6. Create contract info (DRAFT) ===")
r = session.put(f"{BASE}/api/orders/{order_id}/maintenance-contract", json={
    "client_full_name": "Jean Tremblay",
    "company_name": "Tremblay Plomberie inc.",
    "client_email": "jean.tremblay@example.com",
    "client_phone": "418-555-0123",
    "website_concerned": "tremblayplomberie.com",
})
check("contract draft created 200", r.status_code == 200, f"{r.status_code} {r.text}")
contract = r.json()
print("contract draft:", json.dumps(contract, indent=2, default=str))
check("contract status draft", contract.get("status") == "draft")
contract_id = contract.get("id")

print("=== 7. Update contract info again (still draft, should succeed) ===")
r = session.put(f"{BASE}/api/orders/{order_id}/maintenance-contract", json={
    "client_full_name": "Jean Tremblay",
    "company_name": "Tremblay Plomberie & Fils inc.",
    "client_email": "jean.tremblay@example.com",
    "client_phone": "418-555-0123",
    "website_concerned": "tremblayplomberie.com",
})
check("contract draft updated 200", r.status_code == 200, f"{r.status_code} {r.text}")
check("company_name updated", r.json().get("company_name") == "Tremblay Plomberie & Fils inc.")

print("=== 8. Sign without accepting terms -> must fail ===")
r = session.post(f"{BASE}/api/orders/{order_id}/maintenance-contract/sign", json={
    "signer_name": "Jean Tremblay",
    "client_signature_data": "Jean Tremblay",
    "signature_type": "typed",
    "accepted_terms": False,
})
check("sign without acceptance blocked (400)", r.status_code == 400, f"{r.status_code} {r.text}")

print("=== 9. Sign contract (typed signature) ===")
r = session.post(f"{BASE}/api/orders/{order_id}/maintenance-contract/sign", json={
    "signer_name": "Jean Tremblay",
    "client_signature_data": "Jean Tremblay",
    "signature_type": "typed",
    "accepted_terms": True,
})
check("sign 200", r.status_code == 200, f"{r.status_code} {r.text}")
signed_contract = r.json()
print("signed contract:", json.dumps(signed_contract, indent=2, default=str))
check("status signed", signed_contract.get("status") == "signed")
check("has pdf_path", bool(signed_contract.get("pdf_path")))
check("pdf file exists on disk", os.path.exists(signed_contract.get("pdf_path", "")))

print("=== 10. Try to sign again -> must fail ===")
r = session.post(f"{BASE}/api/orders/{order_id}/maintenance-contract/sign", json={
    "signer_name": "Jean Tremblay",
    "client_signature_data": "Jean Tremblay",
    "signature_type": "typed",
    "accepted_terms": True,
})
check("double sign blocked (400)", r.status_code == 400, f"{r.status_code} {r.text}")

print("=== 11. Try to update info after signed -> must fail ===")
r = session.put(f"{BASE}/api/orders/{order_id}/maintenance-contract", json={
    "client_full_name": "Jean Tremblay",
    "company_name": "Autre nom",
    "client_email": "jean.tremblay@example.com",
})
check("update after signed blocked (400)", r.status_code == 400, f"{r.status_code} {r.text}")

print("=== 12. Get order again -> payment_unlocked should now be True ===")
r = session.get(f"{BASE}/api/orders/{order_id}")
order_after = r.json()
print("order after signature:", json.dumps(order_after, indent=2, default=str))
check("payment_unlocked True after signing", order_after.get("payment_unlocked") is True)
check("maintenance_contract_signed True", order_after.get("maintenance_contract_signed") is True)

print("=== 13. Attempt Stripe checkout AFTER contract signed -> should pass payment gate (may fail later on Stripe key, that's fine) ===")
r = session.post(f"{BASE}/api/payments/stripe/checkout", json={"order_id": order_id, "amount_type": "deposit"})
print("stripe checkout status:", r.status_code, r.text[:300])
check("payment gate no longer blocking (not 400 'signer le contrat')", "signer le contrat" not in r.text)

print("=== 13b. Client download own signed contract PDF ===")
r = session.get(f"{BASE}/api/orders/{order_id}/maintenance-contract/download")
check("client download pdf 200", r.status_code == 200, f"{r.status_code}")
check("client pdf content-type", r.headers.get("content-type") == "application/pdf")

print("=== 14. Admin login ===")
admin_session = requests.Session()
r = admin_session.post(f"{BASE}/api/admin/auth/login", json={
    "email": "admin@example.com", "password": "TestAdminPass123!",
})
check("admin login 200", r.status_code == 200, f"{r.status_code} {r.text}")

print("=== 15. Admin list maintenance ===")
r = admin_session.get(f"{BASE}/api/admin/maintenance")
check("admin list maintenance 200", r.status_code == 200, f"{r.status_code} {r.text}")
contracts_list = r.json()
print("admin maintenance list:", json.dumps(contracts_list, indent=2, default=str))
check("contract_status signed in admin list", contracts_list[0].get("contract_status") == "signed" if contracts_list else False)
check("contract_has_pdf True in admin list", contracts_list[0].get("contract_has_pdf") is True if contracts_list else False)

print("=== 16. Admin download signed contract PDF ===")
mc_id = contracts_list[0]["contract_id"]
r = admin_session.get(f"{BASE}/api/admin/maintenance/contracts/{mc_id}/download")
check("admin download pdf 200", r.status_code == 200, f"{r.status_code}")
check("pdf content-type", r.headers.get("content-type") == "application/pdf")
check("pdf non-empty", len(r.content) > 1000)

print("\n=== RESULT ===")
if errors:
    print(f"{len(errors)} test(s) FAILED:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
else:
    print("Tous les tests sont passés.")

server.should_exit = True
time.sleep(1)
