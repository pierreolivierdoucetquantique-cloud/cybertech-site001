"""Test : vérifie qu'aucun doublon n'est généré même avec des requêtes concurrentes."""
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["DATABASE_PATH"] = "./data/test_numbering.db"

from app.database import init_db, SessionLocal
from app.services.numbering import next_invoice_number

if os.path.exists("./data/test_numbering.db"):
    os.remove("./data/test_numbering.db")

init_db()

results = []
errors = []
lock = threading.Lock()


def worker():
    db = SessionLocal()
    try:
        num = next_invoice_number(db)
        with lock:
            results.append(num)
    except Exception as e:
        with lock:
            errors.append(str(e))
    finally:
        db.close()


threads = [threading.Thread(target=worker) for _ in range(50)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"Total générés: {len(results)}")
print(f"Total uniques: {len(set(results))}")
print(f"Erreurs: {len(errors)}")
if errors:
    print("Détail erreurs (5 premières):", errors[:5])

if len(results) == len(set(results)) and len(results) == 50:
    print("✅ SUCCÈS : aucun doublon, tous les numéros générés.")
else:
    print("❌ ÉCHEC : doublons détectés ou numéros manquants.")
    duplicates = [x for x in results if results.count(x) > 1]
    print("Doublons:", set(duplicates))

print("Exemples:", sorted(results)[:5], "...", sorted(results)[-5:])

os.remove("./data/test_numbering.db")
