"""
Migration v9.11 : met à jour l'adresse courriel du compte admin existant
vers cyberteckq@outlook.com.

CONTEXTE : avant la v9.11, l'adresse admin/notification utilisée à travers
la plateforme était cybertechquantum@gmail.com. Le code a été mis à jour
pour utiliser partout cyberteckq@outlook.com, MAIS le compte admin en base
de données (table `admins`, utilisé pour te connecter à Admin > Connexion)
garde l'ancien email tant que ce script n'a pas été exécuté — le code ne
modifie JAMAIS un compte existant automatiquement.

CE QUE FAIT CE SCRIPT :
- Cherche un compte admin dont l'email est cybertechquantum@gmail.com.
- Si trouvé : demande confirmation, puis met à jour son email vers
  cyberteckq@outlook.com. Le mot de passe n'est PAS modifié.
- Si AUCUN compte ne correspond à l'ancien email (ex: tu as déjà changé ton
  email manuellement, ou le compte a été créé directement avec la nouvelle
  adresse) : le script ne touche à rien et te montre les comptes existants
  pour que tu confirmes toi-même lequel ajuster si besoin.
- Si PLUSIEURS comptes admin existent : le script liste tous les comptes et
  s'arrête sans rien modifier, pour éviter de changer le mauvais compte —
  une opération manuelle ciblée est alors plus sûre.

USAGE (à exécuter UNE SEULE FOIS après le déploiement de la v9.11, via le
Shell Render) :

    python tests_manual/migrate_v9_11_admin_email.py
"""
import os
import sys
import datetime as dt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, init_db
from app.models.admin import Admin

OLD_EMAIL = "cybertechquantum@gmail.com"
NEW_EMAIL = "cyberteckq@outlook.com"


def main():
    init_db()
    db = SessionLocal()
    try:
        admins = db.query(Admin).all()

        if not admins:
            print("❌ Aucun compte admin trouvé en base. Rien à migrer.")
            print("   Un compte sera créé automatiquement au prochain démarrage")
            print("   via INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD (variables Render).")
            return

        if len(admins) > 1:
            print(f"⚠️  {len(admins)} comptes admin trouvés — migration automatique annulée par sécurité.")
            print("   Voici les comptes existants :")
            for a in admins:
                print(f"   - {a.id} : {a.email}")
            print()
            print("   Si l'un de ces comptes doit changer d'adresse, indique lequel")
            print("   à Claude (par son email exact) pour un ajustement ciblé.")
            return

        admin = admins[0]

        if admin.email == NEW_EMAIL:
            print(f"✔️  Le compte admin utilise déjà {NEW_EMAIL}. Rien à faire.")
            return

        if admin.email != OLD_EMAIL:
            print(f"ℹ️  Le compte admin actuel utilise une adresse différente de l'ancienne attendue :")
            print(f"   Email actuel  : {admin.email}")
            print(f"   Email attendu : {OLD_EMAIL} (ancien) ou {NEW_EMAIL} (nouveau)")
            print()
            print("   Pour éviter de modifier le mauvais compte, ce script ne touche à rien.")
            print("   Si tu veux quand même changer cette adresse vers la nouvelle, dis-le")
            print("   explicitement à Claude avec l'email exact ci-dessus.")
            return

        print(f"Compte admin trouvé : {admin.email} (id: {admin.id})")
        confirm = input(f"Changer cet email vers {NEW_EMAIL} ? Le mot de passe ne sera PAS modifié. [oui/non] : ").strip().lower()
        if confirm not in ("oui", "o", "yes", "y"):
            print("Annulé — aucune modification effectuée.")
            return

        admin.email = NEW_EMAIL
        db.commit()
        print(f"✅ Email du compte admin mis à jour : {OLD_EMAIL} → {NEW_EMAIL}")
        print("   Connecte-toi désormais avec cette nouvelle adresse (même mot de passe).")

    finally:
        db.close()


if __name__ == "__main__":
    main()
