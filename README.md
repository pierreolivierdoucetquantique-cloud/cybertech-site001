# Cyber Teck Q — Plateforme complète

Site web + espace client + panel admin pour Cyber Teck Q, compilés en un
seul service déployable.

## Structure du projet

```
.
├── app/                    # Backend FastAPI
│   ├── main.py             # Point d'entrée : API + service du site statique
│   ├── config.py           # Variables d'environnement (voir .env.example)
│   ├── database.py         # Connexion SQLite (SQLAlchemy)
│   ├── models/              # Tables de la base de données
│   ├── routers/             # Routes API (auth, commandes, admin, etc.)
│   ├── schemas/              # Validation des données (Pydantic)
│   ├── services/             # Logique métier (facturation, emails, numérotation)
│   └── utils/                 # Sécurité (hash, JWT), rate limiting
├── static_site/             # Frontend (HTML / CSS / JS), servi par le backend
├── data/                     # Base de données locale (ignorée par Git)
├── requirements.txt          # Dépendances Python
├── Dockerfile                # Image de production
├── render.yaml                # Configuration Render (Blueprint)
├── .env.example                # Modèle des variables d'environnement
└── DEPLOIEMENT.md               # Guide de déploiement pas-à-pas
```

## Démarrer en local

```bash
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Remplis .env avec au minimum JWT_SECRET_KEY, INITIAL_ADMIN_EMAIL,
# INITIAL_ADMIN_PASSWORD pour pouvoir te connecter au panel admin.

uvicorn app.main:app --reload
```

Le site est alors accessible sur http://localhost:8000, le panel admin sur
http://localhost:8000/admin-login.html.

## Déployer en production

Voir [DEPLOIEMENT.md](./DEPLOIEMENT.md) pour la procédure complète
(Render + domaine GoDaddy + Resend).

## Sécurité — rappels importants

- Ne jamais commiter de fichier `.env` contenant de vraies valeurs.
- `JWT_SECRET_KEY` doit être unique et secrète en production.
- `INITIAL_ADMIN_EMAIL`/`INITIAL_ADMIN_PASSWORD` ne servent qu'à amorcer le
  premier compte admin ; à retirer du dashboard Render une fois ce compte créé.
- Le panel admin (`/admin-login.html`) n'est lié depuis aucune page publique
  — connu uniquement de l'équipe.
- `STRIPE_SECRET_KEY` et `STRIPE_WEBHOOK_SECRET` sont des secrets au même
  titre que `JWT_SECRET_KEY` : jamais dans le code, jamais dans le chat,
  uniquement dans les variables d'environnement Render.
- Les fichiers téléversés (preuves de paiement, documents clients) vivent
  sur le Render Disk sous `UPLOADS_DIR` et sont servis via `/api/files/{id}`
  avec contrôle d'accès strict (le client ne peut voir que ses propres
  fichiers ; l'admin voit tout).

## Mise à jour v9.10 — Contrat de maintenance électronique

Le **questionnaire technique a été retiré des commandes de type Maintenance**
et remplacé par un **Contrat de Maintenance électronique** :

- Le client complète ses informations (nom, entreprise, courriel, téléphone,
  site concerné), puis **signe électroniquement** le contrat (signature
  dessinée ou nom tapé) après avoir cliqué la case d'acceptation des termes.
- Une fois signé, le contrat est **verrouillé** (plus aucune modification
  possible), un **PDF est généré automatiquement** et envoyé par courriel
  au client et à l'administrateur (cybertechquantum@gmail.com).
- **Le paiement (Interac ou Stripe) d'une commande Maintenance reste bloqué
  jusqu'à la signature du contrat** — exactement comme le paiement d'une
  commande Site Web/Application Mobile reste bloqué tant que le
  questionnaire technique n'est pas soumis. Cette règle est appliquée
  côté serveur (`app/services/payment_gate.py`), donc impossible à
  contourner même en modifiant le frontend.
- **Le questionnaire technique reste inchangé pour les commandes Site Web
  et Application Mobile** — seules les commandes Maintenance sont concernées
  par ce changement.
- Panel admin → **Maintenance** : nouvelle colonne "Contrat" (brouillon /
  signé + date) avec bouton de téléchargement du PDF signé.

**Aucune migration de base de données n'est requise** pour cette mise à
jour : une nouvelle table (`maintenance_contracts`) est ajoutée, et
`Base.metadata.create_all()` crée automatiquement les nouvelles tables au
démarrage (contrairement à l'ajout de colonnes sur une table existante,
qui lui nécessite toujours une migration manuelle — voir la mise à jour
v9.9 ci-dessous).

⚠️ **Avis important** : le texte du contrat de maintenance généré
(engagements de Cyber Teck Q, engagements du client, clause de
renouvellement) est un **modèle standard rédigé pour les besoins de la
plateforme et ne constitue pas un avis juridique**. Il est recommandé de
le faire réviser par un juriste avant une utilisation à grande échelle,
notamment au regard du droit québécois de la consommation et du Code
civil du Québec.

## Mise à jour majeure (paiements, progression, CMS étendu)

Cette version ajoute, par-dessus la base existante :
- Questionnaire technique obligatoire avant tout paiement
- Paiement par virement Interac (preuve + validation admin) et par carte
  (Stripe Checkout + webhook de confirmation automatique)
- Barre de progression du projet synchronisée admin → client (étapes, couleur,
  date de livraison prévue)
- Suppression d'une commande en attente côté client ("panier")
- CMS étendu : galerie multi-images/vidéo pour les réalisations, coordonnées
  de contact (courriel, téléphone, adresse, réseaux sociaux) éditables sans
  toucher au code, documents admin → client
- Prix du contrat de maintenance : 499 $ (était 299 $)
- **Connexion unifiée** : le formulaire de connexion sur `creation-site-web.html`
  essaie maintenant automatiquement la connexion client, puis (en cas
  d'échec) la connexion admin avec les mêmes identifiants. `admin-login.html`
  reste fonctionnel en parallèle si tu préfères t'y connecter directement.

## CMS complet du contenu des pages publiques

Toutes les pages publiques (Accueil, Services, Tarifs, Création de votre
site Web, FAQ, Contact, navigation et pied de page) sont maintenant
éditables depuis **Panel admin → Contenu du site → Pages du site** :
- Tous les titres, sous-titres, textes de boutons et liens de boutons
- Les listes éditables avec ajout/suppression/réordonnancement : étapes de
  "Notre histoire", valeurs de la mission, barre de confiance, mots animés
  du Hero, cartes de service, étapes du processus, conditions de paiement
- Le portfolio de la page d'accueil est maintenant connecté aux
  "Réalisations" gérées dans **Panel admin → Projets** (il affichait
  auparavant une seule réalisation codée en dur, indépendamment du CRM)

L'historique des modifications avec restauration de version (demandé dans
le cahier des charges mais volontairement reporté, vu l'ampleur du
chantier) reste à construire dans une session future.

**Si tu mets à jour un site déjà en production avec une base de données
existante**, voir la section dédiée dans `DEPLOIEMENT.md` — une étape de
migration manuelle est nécessaire (sinon le site plantera au démarrage).

À venir dans une prochaine session : rendre la page d'accueil et la page
Services entièrement éditables depuis le CMS (textes, images, vidéos,
arrière-plans), tel que demandé dans le cahier des charges.
