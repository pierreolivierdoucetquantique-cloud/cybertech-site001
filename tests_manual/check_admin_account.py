"""
Script de diagnostic : vérifie si un compte admin existe en base.

À lancer depuis le Shell Render (bouton "Shell" dans le dashboard du
service), une fois connecté à l'instance en production :

    python3 tests_manual/check_admin_account.py

Ce script ne modifie RIEN — il ne fait que lire et afficher l'état actuel,
pour savoir quoi faire ensuite (créer le premier compte via
INITIAL_ADMIN_EMAIL/INITIAL_ADMIN_PASSWORD, ou réinitialiser un mot de passe
oublié).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal, init_db
from app.models.admin import Admin

init_db()
db = SessionLocal()

admins = db.query(Admin).all()

if not admins:
    print("❌ Aucun compte admin trouvé en base de données.")
    print()
    print("Pour en créer un :")
    print("  1. Va sur Render → ton service → onglet Environment")
    print("  2. Ajoute (ou vérifie la valeur de) INITIAL_ADMIN_EMAIL et INITIAL_ADMIN_PASSWORD")
    print("  3. Sauvegarde — le service redémarre et crée le compte automatiquement")
    print("  4. Connecte-toi avec ces mêmes identifiants")
else:
    print(f"✅ {len(admins)} compte(s) admin trouvé(s) :")
    print()
    for a in admins:
        status = "actif" if a.is_active else "DÉSACTIVÉ"
        locked = ""
        if a.locked_until:
            import datetime as dt
            if a.locked_until > dt.datetime.utcnow():
                locked = f" — VERROUILLÉ jusqu'à {a.locked_until} UTC"
        print(f"  - {a.email} ({status}{locked}, {a.failed_login_attempts} échec(s) récent(s))")
    print()
    print("Si tu ne te souviens plus du mot de passe d'un de ces comptes,")
    print("dis-le à Claude avec l'email exact ci-dessus : il pourra te guider")
    print("pour réinitialiser le mot de passe directement en base (lui non plus")
    print("ne peut pas connaître ou choisir ton mot de passe à ta place pour")
    print("des raisons de sécurité, mais il peut t'aider à le changer toi-même).")

db.close()
