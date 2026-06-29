# Guide de déploiement — Cyber Teck Q

Ce guide t'amène du code que tu as sur ton ordinateur jusqu'à un site
fonctionnel sur `https://cyberteckq.com` (ou ton domaine), hébergé sur
Render, avec GoDaddy qui ne sert que pour le nom de domaine.

Compte ~30-45 minutes pour la première mise en ligne.

---

## 0. Avant de commencer — vérifier ce que tu as

- [ ] Un compte Render créé
- [ ] Un repo GitHub (ou GitLab) créé pour ce projet
- [ ] Un compte Resend avec une clé API
- [ ] Ton domaine acheté sur GoDaddy
- [ ] Le dossier complet du projet (celui que tu es en train de lire)

---

## 1. Mettre le code sur GitHub

Si ton repo est vide, depuis le dossier du projet :

```bash
git init
git add .
git commit -m "Premier déploiement Cyber Teck Q"
git branch -M main
git remote add origin https://github.com/TON-USERNAME/TON-REPO.git
git push -u origin main
```

**Vérifie que le fichier `.env` n'est PAS dans ton repo** (le `.gitignore`
fourni l'exclut automatiquement). Si tu avais déjà un `.env` avec de vraies
valeurs, ne le commite jamais — change les valeurs sensibles (clé Resend,
mot de passe admin) si elles ont été exposées par erreur.

---

## 2. Créer le service sur Render

### Option A — Avec le fichier render.yaml (recommandé, plus rapide)

1. Dans le dashboard Render, clique **New +** → **Blueprint**.
2. Connecte ton repo GitHub.
3. Render détecte automatiquement `render.yaml` et te propose de créer :
   - Un **Web Service** nommé `cyberteckq`
   - Un **Disk** persistant de 1 GB monté sur `/app/data`
4. Clique **Apply**. Render commence le premier déploiement.

### Option B — Configuration manuelle

1. **New +** → **Web Service** → connecte ton repo.
2. Renseigne :
   - **Runtime** : Docker
   - **Region** : la plus proche de tes clients (ex: Oregon ou un région canadienne si disponible)
   - **Plan** : Starter (suffisant pour démarrer)
3. Onglet **Disks** → **Add Disk** :
   - **Name** : `cyberteckq-data`
   - **Mount Path** : `/app/data`
   - **Size** : 1 GB
4. Onglet **Settings** → **Health Check Path** : `/api/health`

---

## 3. Configurer les variables d'environnement sur Render

Dans le service → onglet **Environment**, ajoute (ou vérifie, si tu as
utilisé le Blueprint) chacune de ces variables. Réfère-toi à `.env.example`
pour la description complète de chacune.

| Variable | Valeur à mettre |
|---|---|
| `ENVIRONMENT` | `production` |
| `DATABASE_PATH` | `/app/data/cyberteckq.db` |
| `UPLOADS_DIR` | `/app/data/uploads` |
| `COOKIE_SECURE` | `True` |
| `JWT_SECRET_KEY` | Générée automatiquement par le Blueprint, sinon génère-la toi-même (voir `.env.example`) |
| `RESEND_API_KEY` | Ta clé API Resend (commence par `re_`) |
| `EMAIL_FROM` | Ex: `Cyber Teck Q <contact@cyberteckq.com>` — **doit utiliser un domaine vérifié dans Resend**, voir étape 6 |
| `ADMIN_NOTIFICATION_EMAIL` | `cybertechquantum@gmail.com` (ou l'adresse où tu veux recevoir les notifications) |
| `FRONTEND_URL` | `https://cyberteckq.com` (ton domaine final, avec https) |
| `INITIAL_ADMIN_EMAIL` | L'adresse avec laquelle TU te connecteras au panel admin |
| `INITIAL_ADMIN_PASSWORD` | Un mot de passe fort (12+ caractères, lettres + chiffres) |
| `INTERAC_EMAIL` | `cybertechquantum@gmail.com` (adresse affichée au client pour le virement) |
| `STRIPE_SECRET_KEY` | Ta clé secrète Stripe (`sk_live_...` ou `sk_test_...` pour essayer d'abord) |
| `STRIPE_PUBLISHABLE_KEY` | Ta clé publique Stripe (`pk_live_...` ou `pk_test_...`) |
| `STRIPE_WEBHOOK_SECRET` | Voir étape 6.1 ci-dessous — généré après création du webhook |

Clique **Save Changes**. Render redéploie automatiquement avec les nouvelles
variables.

---

## 4. Premier déploiement et vérification

1. Onglet **Logs** : surveille le déploiement. Tu dois voir à la fin :
   ```
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://0.0.0.0:XXXX
   ```
2. Render te donne une URL temporaire du type `https://cyberteckq.onrender.com`.
   Ouvre-la : ton site doit s'afficher normalement.
3. Va sur `https://cyberteckq.onrender.com/admin-login.html` et connecte-toi
   avec `INITIAL_ADMIN_EMAIL` / `INITIAL_ADMIN_PASSWORD`. Tu dois arriver sur
   le panel admin.

**Important — après cette première connexion réussie :** retourne dans
**Environment** sur Render et **supprime** les variables
`INITIAL_ADMIN_EMAIL` et `INITIAL_ADMIN_PASSWORD`. Elles ne servent qu'à
créer le premier compte ; les laisser ne pose pas de risque immédiat (elles
ne sont relues que si la table des admins est vide), mais c'est une bonne
pratique de les retirer une fois le compte créé.

### En cas de problème de connexion admin

Si tu n'arrives pas à te connecter au panel admin, lance ce diagnostic
depuis le Shell Render (ton service → bouton **Shell**) — il ne fait que
lire la base, sans rien modifier :

```bash
python3 tests_manual/check_admin_account.py
```

Il te dira si un compte admin existe déjà ou non, et avec quel statut
(actif, désactivé, verrouillé). C'est la première chose à vérifier avant
de chercher plus loin.

---

## 5. Brancher ton domaine GoDaddy

### Sur Render

1. Service → onglet **Settings** → **Custom Domains** → **Add Custom Domain**.
2. Entre ton domaine : `cyberteckq.com` (et `www.cyberteckq.com` si tu veux les deux).
3. Render t'affiche les enregistrements DNS à créer (généralement un `CNAME`
   pour `www` et soit un `A` record soit un `ALIAS`/`ANAME` pour le domaine racine).

### Sur GoDaddy

1. Connecte-toi à GoDaddy → **Mes produits** → ton domaine → **DNS** → **Gérer les DNS**.
2. Supprime les enregistrements `A` ou `CNAME` par défaut de GoDaddy qui
   pointent vers leur page de parking, s'il y en a.
3. Ajoute les enregistrements exacts que Render t'a donnés à l'étape précédente :
   - Type `CNAME`, nom `www`, valeur fournie par Render (ex: `cyberteckq.onrender.com`)
   - Pour le domaine racine (`cyberteckq.com` sans www), suis l'option que
     Render propose (souvent un enregistrement `A` vers une IP fournie, ou
     `ALIAS`/`ANAME` selon le support de GoDaddy)
4. Sauvegarde. La propagation DNS prend de quelques minutes à quelques heures
   (rarement plus de 24h).
5. Une fois propagé, Render détecte le domaine et **génère automatiquement un
   certificat HTTPS gratuit** (Let's Encrypt) — aucune action de ta part.

### Mettre à jour FRONTEND_URL

Une fois le domaine actif, retourne dans **Environment** sur Render et mets
à jour `FRONTEND_URL` avec ton vrai domaine final (`https://cyberteckq.com`),
puis sauvegarde pour redéployer.

---

## 6. Configurer Resend pour un vrai domaine d'envoi

Par défaut, Resend permet d'envoyer depuis `onboarding@resend.dev` (limité,
pratique seulement pour les tests). Pour envoyer depuis `contact@cyberteckq.com` :

1. Dans le dashboard Resend → **Domains** → **Add Domain** → entre `cyberteckq.com`.
2. Resend te donne des enregistrements DNS (`TXT`, `MX`, parfois `CNAME` pour
   DKIM) à ajouter — exactement comme à l'étape 5, mais cette fois dans
   GoDaddy DNS pour la vérification d'envoi d'emails.
3. Une fois les enregistrements ajoutés et vérifiés (statut "Verified" dans
   Resend), tu peux utiliser n'importe quelle adresse `@cyberteckq.com` comme
   `EMAIL_FROM`.

---

## 6.1. Configurer le webhook Stripe

Le paiement par carte (Stripe Checkout) fonctionne sans webhook, mais le
webhook est ce qui confirme **automatiquement** la commande une fois le
paiement réussi (sinon il faudrait valider chaque paiement manuellement).

1. Connecte-toi à [dashboard.stripe.com/webhooks](https://dashboard.stripe.com/webhooks).
2. **Add endpoint** → URL : `https://cyberteckq.com/api/webhooks/stripe`
   (remplace par ton domaine réel, ou l'URL `.onrender.com` temporaire si le
   domaine n'est pas encore branché).
3. Événement à sélectionner : `checkout.session.completed` (un seul suffit).
4. Une fois créé, Stripe affiche un **Signing secret** (commence par `whsec_`).
   Copie-le dans la variable `STRIPE_WEBHOOK_SECRET` sur Render.
5. Sauvegarde sur Render — le service redéploie.
6. Pour tester : fais un paiement test avec une carte de test Stripe
   (`4242 4242 4242 4242`, n'importe quelle date future, n'importe quel CVC)
   depuis l'espace client, onglet **Paiement**. Le statut de la commande doit
   passer à "Dépôt reçu" ou "Payé" automatiquement après quelques secondes.

**Important** : tant que `STRIPE_SECRET_KEY` n'est pas configurée, le bouton
"Payer par carte" affichera une erreur explicite au client plutôt qu'un
plantage — le virement Interac reste utilisable en attendant.

---

## Mettre à jour un site déjà en ligne (pas un premier déploiement)

Si Cyber Teck Q tourne déjà en production et que tu déploies cette mise à
jour par-dessus une base de données existante, une étape **supplémentaire et
obligatoire** s'ajoute : cette mise à jour ajoute de nouvelles colonnes à des
tables qui existent déjà (`orders.expected_delivery_date`,
`projects.video_url`) et de nouvelles tables (`payments`, `uploaded_files`).

SQLite ne crée automatiquement que les tables **manquantes** au démarrage —
il ne modifie jamais une table déjà existante. Sans intervention, le site
plantera au premier appel touchant une commande ou un projet, avec une
erreur du type `no such column`.

**Avant de pousser cette mise à jour en production**, deux options :

### Option A — Le plus simple : repartir d'une base neuve (si tu n'as pas
encore de vrais clients/commandes en production)
Sur Render, va dans le Disk attaché au service et supprime simplement le
fichier `cyberteckq.db`. Au redémarrage, toutes les tables (anciennes et
nouvelles) seront créées proprement. **Tu perds toutes les données existantes**
— ne fais ceci que si la base actuelle ne contient que des données de test.

### Option B — Conserver les données existantes (recommandé si tu as déjà
de vrais clients)
Il faut ajouter les colonnes manquantes manuellement, une seule fois, avant
ou juste après le déploiement. Depuis un shell connecté au service Render
(Render → ton service → **Shell**), lance :

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/cyberteckq.db')
cur = conn.cursor()
for stmt in [
    \"ALTER TABLE orders ADD COLUMN expected_delivery_date DATE\",
    \"ALTER TABLE projects ADD COLUMN video_url VARCHAR\",
]:
    try:
        cur.execute(stmt)
        print('OK:', stmt)
    except sqlite3.OperationalError as e:
        print('Déjà présent ou erreur (normal si déjà appliqué) :', e)
conn.commit()
conn.close()
"
```

Les nouvelles tables (`payments`, `uploaded_files`, `repeatable_items`) n'ont pas besoin de cette
étape : SQLAlchemy les crée automatiquement au démarrage puisqu'elles
n'existaient pas avant.

**Note sur le prix du contrat de maintenance (299 $ → 499 $)** : si la base
de données existe déjà en production, le nouveau prix ne s'applique pas
automatiquement à la FAQ ni aux tarifs publics (ces textes sont stockés en
base, pas dans le code, justement pour que tu puisses les modifier toi-même).
Après le déploiement, va dans **Panel admin → Contenu du site** et modifie
manuellement :
- Le forfait "Maintenance" (section Tarifs) → change le prix pour `499 $ CAD / an`
- La question FAQ "En quoi consiste le contrat de maintenance ?" → remplace `299 $` par `499 $` dans la réponse

Le prix utilisé lors d'une nouvelle commande (`/api/marketplace`), lui, est
déjà à jour automatiquement avec ce déploiement — seul l'affichage des pages
FAQ/Tarifs nécessite cette petite retouche manuelle si la base existait déjà.

Si jamais tu n'es pas certain ou que quelque chose ne fonctionne pas après
cette étape, dis-le-moi avec le message d'erreur exact des logs Render —
je pourrai te guider précisément.

---

## 7. Vérifications finales (checklist)

Une fois le domaine actif et HTTPS confirmé (cadenas dans le navigateur) :

- [ ] `https://cyberteckq.com` affiche bien la page d'accueil
- [ ] Inscription d'un compte client test fonctionne (`creation-site-web.html`)
- [ ] Une commande test peut être passée depuis `mon-compte.html`
- [ ] Le bouton "Payer" reste bloqué tant que le questionnaire technique n'est pas rempli, avec le message d'avertissement visible
- [ ] Après avoir rempli le questionnaire, l'onglet "Paiement" devient accessible pour cette commande
- [ ] Un virement Interac test (upload de preuve) apparaît bien dans l'onglet admin "Paiements", en attente de validation
- [ ] Valider ce paiement test côté admin met bien à jour le statut de la commande et génère une facture
- [ ] Un paiement test Stripe (carte `4242 4242 4242 4242`) confirme automatiquement la commande (voir étape 6.1)
- [ ] Le curseur d'avancement du projet, modifié côté admin, se reflète immédiatement dans l'espace client (pourcentage, étape, couleur)
- [ ] Le bouton "Supprimer" sur une commande en attente fonctionne côté client, avec confirmation
- [ ] L'admin peut ajouter une image/vidéo à la galerie d'une réalisation et la voir apparaître sur le portfolio public
- [ ] La connexion admin fonctionne sur `https://cyberteckq.com/admin-login.html`
- [ ] Modifier le statut de paiement d'une commande test admin génère bien une facture PDF téléchargeable
- [ ] Le formulaire de contact arrive bien dans la boîte définie par `ADMIN_NOTIFICATION_EMAIL`
- [ ] Les variables `INITIAL_ADMIN_EMAIL`/`INITIAL_ADMIN_PASSWORD` ont été retirées de Render après la création du premier admin
- [ ] Supprime ensuite le compte client test que tu as créé pour les vérifications (`mon-compte.html` → Paramètres → Supprimer mon compte)

---

## Notes pour la suite

- **Sauvegardes** : la base de données SQLite vit entièrement sur le Render
  Disk. Render ne fait pas de sauvegarde automatique des Disks sur le plan
  Starter — pense à exporter régulièrement le fichier `cyberteckq.db` si le
  volume de données devient important (Render permet de s'y connecter en SSH
  via `render shell` sur les plans qui le supportent, ou via un export
  périodique que l'on peut ajouter plus tard si besoin).
- **Mise à jour du site** : à chaque `git push` sur la branche `main`, Render
  redéploie automatiquement la dernière version.
- **Limite technique à connaître** : comme indiqué plus tôt dans notre
  conversation, un Render Disk ne fonctionne qu'avec une seule instance du
  service (pas de scaling horizontal). C'est suffisant pour le volume actuel
  de Cyber Teck Q ; si le trafic grandit beaucoup, il faudra migrer vers une
  vraie base de données managée (PostgreSQL Render) — ce serait un projet
  séparé le jour où ce sera nécessaire.
