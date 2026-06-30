"""
Pré-remplissage initial du CMS (FAQ + tarifs) au premier démarrage.

Sans ce seed, les tables faq_entries et pricing_plans démarrent vides, ce qui
ferait apparaître les pages publiques /faq.html et /tarifs.html sans aucun
contenu tant que l'admin n'a rien saisi manuellement dans le panneau admin.

Ce script reproduit exactement le contenu qui était auparavant codé en dur
dans le HTML, pour que le premier déploiement reste identique visuellement.
L'admin peut ensuite tout modifier normalement via /admin-dashboard.html
(panneau "Contenu du site").

Comme bootstrap_initial_admin, ce seed ne fait rien si du contenu existe déjà
— il ne s'exécute donc qu'une seule fois, au tout premier démarrage.
"""
import json
import logging

from sqlalchemy.orm import Session

from app.models.content import FaqEntry, PricingPlan, ContentBlock, RepeatableItem

logger = logging.getLogger("ctq.cms_seed")

DEFAULT_CONTENT_BLOCKS = [
    ("contact.email", "Courriel de contact", "cyberteckq@outlook.com"),
    ("contact.phone", "Téléphone", ""),
    ("contact.address", "Adresse", ""),
    ("contact.social_facebook", "Lien Facebook", ""),
    ("contact.social_instagram", "Lien Instagram", ""),
    ("contact.social_linkedin", "Lien LinkedIn", ""),

    # --- Navigation (globale) ---
    ("nav.link_accueil", "Lien — Accueil", "Accueil"),
    ("nav.link_services", "Lien — Services", "Services"),
    ("nav.link_tarifs", "Lien — Tarifs", "Tarifs"),
    ("nav.link_creation", "Lien — Création de votre site Web", "Création de votre site Web"),
    ("nav.link_faq", "Lien — FAQ", "FAQ"),
    ("nav.link_contact", "Lien — Contact", "Contact"),

    # --- Footer (global) ---
    ("footer.tagline", "Footer — slogan", "Imaginer. Créer. Développer. Propulser vos idées."),
    ("footer.copyright", "Footer — texte de copyright (après l'année)", "Cyber Teck Q. Tous droits réservés."),

    # --- index.html : Hero ---
    ("home.hero.line1", "Accueil Hero — ligne 1", "DES SOLUTIONS WEB"),
    ("home.hero.line2_prefix", "Accueil Hero — ligne 2 (avant les mots animés)", "QUI VOUS"),
    ("home.hero.line3", "Accueil Hero — ligne 3", "VERS LE SUCCÈS"),
    ("home.hero.subtitle", "Accueil Hero — sous-titre", "Conception de sites web performants et solutions numériques sur mesure"),
    ("home.hero.button_text", "Accueil Hero — texte du bouton", "Découvrir mes services"),
    ("home.hero.button_link", "Accueil Hero — lien du bouton", "services.html"),

    # --- index.html : Notre histoire ---
    ("home.story.eyebrow", "Histoire — eyebrow", "D'où nous venons"),
    ("home.story.title", "Histoire — titre", "Notre histoire"),
    ("home.story.subtitle", "Histoire — sous-titre", "Là où la créativité rencontre la technologie."),
    ("home.story.quote_text", "Histoire — citation", "Le site web que tu construiras sera la limite de ton imagination."),
    ("home.story.quote_followup", "Histoire — texte après la citation", "À cet instant, une seule pensée m'est venue : « Mon imagination n'a aucune limite. » C'est ainsi que l'aventure a commencé."),

    # --- index.html : Mission ---
    ("home.mission.eyebrow", "Mission — eyebrow", "Notre mission"),
    ("home.mission.title", "Mission — titre", "Bienvenue chez Cyber Tek Q"),
    ("home.mission.lead", "Mission — texte d'intro", "Là où la créativité rencontre la technologie. Nous concevons des sites web modernes, performants et évolutifs qui mettent votre entreprise en valeur et transforment votre vision en une expérience numérique professionnelle."),
    ("home.mission.paragraph2", "Mission — paragraphe 2", "Que vous soyez entrepreneur, travailleur autonome, PME ou organisme, nous développons des solutions adaptées à vos besoins. Chaque projet est conçu avec soin afin d'offrir une identité forte, une navigation intuitive, une sécurité fiable et une expérience utilisateur agréable."),
    ("home.mission.paragraph3", "Mission — paragraphe 3", "Pour nous, chaque site web est bien plus qu'une vitrine\u00a0: c'est un outil qui représente votre entreprise, inspire confiance à vos clients et accompagne votre croissance."),
    ("home.mission.closing", "Mission — phrase de clôture", "Des solutions qui vous ressemblent."),

    # --- index.html : Portfolio ---
    ("home.portfolio.eyebrow", "Réalisations — eyebrow", "Nos réalisations"),
    ("home.portfolio.title", "Réalisations — titre", "Des projets qui parlent d'eux-mêmes"),
    ("home.portfolio.subtitle", "Réalisations — sous-titre", "Chaque site est conçu sur mesure pour refléter l'identité et les objectifs de nos clients."),
    ("home.portfolio.cta_text", "Réalisations — texte du bouton", "Démarrer mon projet"),
    ("home.portfolio.cta_link", "Réalisations — lien du bouton", "contact.html"),

    # --- services.html ---
    ("services.hero.eyebrow", "Services Hero — eyebrow", "Ce que nous proposons"),
    ("services.hero.title", "Services Hero — titre", "Nos Services"),
    ("services.hero.subtitle", "Services Hero — sous-titre", "Des solutions complètes pour lancer, propulser et faire évoluer votre présence en ligne."),
    ("services.process.eyebrow", "Services Process — eyebrow", "Comment ça fonctionne"),
    ("services.process.title", "Services Process — titre", "Un processus simple et transparent"),
    ("services.cta.title", "Services CTA — titre", "Vos idées deviennent réalité."),
    ("services.cta.text", "Services CTA — texte", "Discutons de votre projet dès aujourd'hui."),
    ("services.cta.button_text", "Services CTA — texte du bouton", "Discuter de mon projet"),
    ("services.cta.button_link", "Services CTA — lien du bouton", "contact.html"),

    # --- tarifs.html ---
    ("tarifs.hero.eyebrow", "Tarifs Hero — eyebrow", "Investissement"),
    ("tarifs.hero.title", "Tarifs Hero — titre", "Tarifs"),
    ("tarifs.hero.subtitle", "Tarifs Hero — sous-titre", "Des forfaits clairs et adaptés à vos besoins pour la création de votre site web."),
    ("tarifs.note", "Tarifs — note sous les forfaits", "Les modifications supplémentaires au-delà des 3 gratuites sont facturées selon l'ampleur des travaux. Paiements sécurisés, données protégées selon les normes canadiennes et québécoises (Loi 25)."),
    ("tarifs.conditions.title", "Tarifs — titre conditions de paiement", "Conditions de paiement"),
    ("tarifs.cta.title", "Tarifs CTA — titre", "Une question sur nos forfaits ?"),
    ("tarifs.cta.text", "Tarifs CTA — texte", "Je réponds rapidement à toutes vos questions."),
    ("tarifs.cta.button_text", "Tarifs CTA — texte du bouton", "Poser ma question"),
    ("tarifs.cta.button_link", "Tarifs CTA — lien du bouton", "contact.html"),

    # --- creation-site-web.html ---
    ("creation.hero.eyebrow", "Création Hero — eyebrow", "Création de votre site Web"),
    ("creation.hero.title", "Création Hero — titre", "Votre espace client"),
    ("creation.hero.subtitle", "Création Hero — sous-titre", "La création de votre site Web débute par l'ouverture de votre espace client."),
    ("creation.section.subtitle", "Création — sous-titre section", "Suivez vos projets, vos factures et vos documents en un seul endroit sécurisé."),

    # --- faq.html ---
    ("faq.hero.eyebrow", "FAQ Hero — eyebrow", "Questions fréquentes"),
    ("faq.hero.title", "FAQ Hero — titre", "Tout ce qu'il faut savoir"),
    ("faq.hero.subtitle", "FAQ Hero — sous-titre", "Les réponses aux questions les plus posées avant de démarrer un projet."),
    ("faq.cta.button_text", "FAQ — texte du bouton final", "D'autres questions ? Contactez-nous"),
    ("faq.cta.button_link", "FAQ — lien du bouton final", "contact.html"),

    # --- contact.html ---
    ("contact.hero.eyebrow", "Contact Hero — eyebrow", "Parlons de votre projet"),
    ("contact.hero.title", "Contact Hero — titre", "Me Contacter"),
    ("contact.hero.subtitle", "Contact Hero — sous-titre", "Une question, un projet en tête ? Écrivez-moi et je vous réponds rapidement."),
    ("contact.alt.eyebrow", "Contact — eyebrow \"aussi par courriel\"", "Aussi par courriel"),
]


DEFAULT_FAQ = [
    (
        "Comment se déroule la création de mon site web ?",
        "Tout commence par l'ouverture de votre espace client. Une fois votre "
        "commande confirmée, vous remplissez un questionnaire technique qui "
        "nous permet de bien cerner vos besoins, puis nous concevons, "
        "développons et lançons votre site selon l'entente convenue.",
    ),
    (
        "À quoi sert mon compte client ?",
        "Votre espace client centralise vos commandes, vos factures, vos "
        "documents et l'avancement de votre projet, en un seul endroit "
        "sécurisé et accessible à tout moment.",
    ),
    (
        "Qu'est-ce que le formulaire technique ?",
        "Après votre commande, vous remplissez un court questionnaire "
        "(entreprise, objectifs, couleurs souhaitées, fonctionnalités, etc.) "
        "qui nous est transmis automatiquement. Il nous permet de démarrer "
        "votre projet avec une vision claire dès le départ.",
    ),
    (
        "Y a-t-il une rencontre prévue avec vous ?",
        "Oui. Après réception de votre questionnaire, nous planifions une "
        "rencontre par Messenger ou Zoom afin de discuter des détails de "
        "votre projet et répondre à vos questions.",
    ),
    (
        "Combien de temps prend un projet ?",
        "Les délais varient selon la complexité du projet. Un site standard "
        "prend généralement de 2 à 4 semaines après la réception complète "
        "de vos informations et contenus.",
    ),
    (
        "Comment fonctionnent les paiements ?",
        "Un dépôt de 40\u00a0% est requis pour démarrer le projet, et le solde "
        "est payable selon l'entente convenue. Les virements bancaires sont "
        "acceptés. Une facture officielle vous est remise pour chaque "
        "commande.",
    ),
    (
        "Combien de révisions gratuites sont incluses ?",
        "3 révisions gratuites sont incluses avec la création de votre site "
        "web. Les modifications supplémentaires sont facturées selon "
        "l'ampleur des travaux.",
    ),
    (
        "En quoi consiste le contrat de maintenance ?",
        "Pour 499 $ CAD par année, votre site bénéficie de mises à jour, de "
        "sauvegardes automatisées, d'une sécurité renforcée et d'un support "
        "prioritaire.",
    ),
    (
        "Faites-vous aussi des applications mobiles ?",
        "Oui. Nous développons des applications Android et iOS avec une "
        "interface moderne, à partir de 399 $ CAD, incluant la publication "
        "sur les boutiques d'applications.",
    ),
    (
        "Comment obtenir du support après le lancement ?",
        "Vous pouvez nous écrire directement à cyberteckq@outlook.com "
        "ou via votre espace client. Les clients avec un contrat de "
        "maintenance bénéficient d'un support prioritaire.",
    ),
]

DEFAULT_PRICING = [
    {
        "name": "Site Web",
        "price": "1 300 $ CAD",
        "features": [
            "Responsive",
            "SEO",
            "Design sur mesure",
            "Optimisation de la performance",
            "3 révisions gratuites",
        ],
        "is_featured": False,
    },
    {
        "name": "Application Mobile",
        "price": "399 $ CAD",
        "features": [
            "Android",
            "iOS",
            "Interface moderne (UI)",
            "Publication sur les boutiques d'applications",
        ],
        "is_featured": True,
    },
    {
        "name": "Maintenance",
        "price": "499 $ CAD / an",
        "features": [
            "Mises à jour",
            "Sauvegardes",
            "Sécurité",
            "Optimisation",
            "Support prioritaire",
        ],
        "is_featured": False,
    },
]

# Groupes d'items répétables : (group_key, [ {champs...}, ... ])
DEFAULT_REPEATABLE_ITEMS: dict[str, list[dict]] = {

    "home.hero.typed_words": [
        {"word": "PROPULSENT"},
        {"word": "INSPIRENT"},
        {"word": "TRANSFORMENT"},
        {"word": "CONNECTENT"},
    ],

    "home.story.steps": [
        {
            "tag": "La rencontre",
            "text": "La naissance de Cyber Tek Q est le fruit d'une rencontre qui a marqué mon parcours. Un homme, à quelques pas d'une retraite bien méritée après avoir consacré toute sa vie au domaine de l'informatique, est arrivé sur mon chemin. À cette époque, j'étais une véritable page blanche. Je ne possédais aucune connaissance en développement web.",
            "icon": "people",
        },
        {
            "tag": "L'apprentissage",
            "text": "Au fil des semaines, grâce à ses conseils, à ma volonté d'apprendre et à beaucoup de détermination, j'ai commencé à découvrir un univers fascinant.",
            "icon": "compass",
        },
        {
            "tag": "Le déclic",
            "text": "",  # cette étape utilise quote_text/quote_followup (ContentBlock) plutôt qu'un texte simple
            "icon": "quote",
            "is_quote": True,
        },
        {
            "tag": "Aujourd'hui",
            "text": "Aujourd'hui, Cyber Tek Q est né de cette passion pour la création et du désir d'aider les entreprises à se démarquer grâce à des solutions numériques modernes, simples et efficaces.",
            "icon": "rocket",
        },
    ],

    "home.mission.values": [
        {"text": "Nous imaginons", "icon": "star"},
        {"text": "Nous créons", "icon": "rocket"},
        {"text": "Nous développons", "icon": "gear"},
    ],

    "home.trust_items": [
        {"text": "Performance<br>Optimisée", "icon": "clock"},
        {"text": "Sécurité<br>Avancée", "icon": "shield"},
        {"text": "Design Adaptatif<br>Tous Écrans", "icon": "device"},
        {"text": "Référencement<br>Naturel (SEO)", "icon": "search"},
        {"text": "Support &<br>Accompagnement", "icon": "support"},
    ],

    "services.cards": [
        {
            "title": "Création de site Web",
            "text": "Un site conçu autour de vos objectifs, rapide, bien structuré, et pensé pour convertir vos visiteurs en clients.",
            "icon": "rocket",
            "features": ["Responsive (mobile & tablette)", "Design sur mesure", "Performance optimisée", "Formation incluse", "3 révisions gratuites"],
            "button_text": "Voir les tarifs",
            "button_link": "tarifs.html",
        },
        {
            "title": "Maintenance",
            "text": "Assurez la performance, la sécurité et la tranquillité d'esprit de votre site web, en continu.",
            "icon": "shield",
            "features": ["Mises à jour régulières", "Sauvegardes automatisées", "Sécurité renforcée", "Correction de bugs", "Support technique"],
            "button_text": "Voir les tarifs",
            "button_link": "tarifs.html",
        },
        {
            "title": "Application Mobile",
            "text": "Une présence mobile soignée, pensée pour vos clients où qu'ils se trouvent.",
            "icon": "automation",
            "features": ["Android", "iPhone (iOS)", "Interface moderne (UI)", "Publication sur l'App Store"],
            "button_text": "Voir les tarifs",
            "button_link": "tarifs.html",
        },
        {
            "title": "Accompagnement",
            "text": "Du premier appel jusqu'au lancement et au-delà, nous restons votre point de contact unique.",
            "icon": "support",
            "features": ["Analyse des besoins", "Consultation", "Suivi de projet", "Support après-vente"],
            "button_text": "Nous contacter",
            "button_link": "contact.html",
        },
    ],

    "services.process_steps": [
        {"number": "01", "title": "Découverte", "text": "On discute de vos besoins, votre marché et vos objectifs pour cadrer le projet."},
        {"number": "02", "title": "Conception", "text": "Nous concevons la structure et le design en fonction de votre image de marque."},
        {"number": "03", "title": "Développement", "text": "Le site est codé, testé et optimisé pour la performance et le référencement."},
        {"number": "04", "title": "Lancement", "text": "Mise en ligne, formation rapide et 3 modifications gratuites incluses."},
    ],

    "tarifs.conditions_items": [
        {"text": "Un dépôt de 40\u00a0% est requis pour démarrer le projet."},
        {"text": "Le solde restant est payable selon l'entente convenue."},
        {"text": "Les virements bancaires sont acceptés."},
    ],
}


def seed_default_cms_content(db: Session) -> None:
    if db.query(FaqEntry).count() == 0:
        for order, (question, answer) in enumerate(DEFAULT_FAQ):
            db.add(FaqEntry(
                question=question,
                answer=answer,
                display_order=order,
                is_published=True,
            ))
        logger.info("FAQ par défaut insérée (%d questions).", len(DEFAULT_FAQ))

    if db.query(PricingPlan).count() == 0:
        for order, plan in enumerate(DEFAULT_PRICING):
            db.add(PricingPlan(
                name=plan["name"],
                price=plan["price"],
                features=json.dumps(plan["features"], ensure_ascii=False),
                is_featured=plan["is_featured"],
                display_order=order,
                is_published=True,
            ))
        logger.info("Forfaits tarifaires par défaut insérés (%d).", len(DEFAULT_PRICING))

    for key, label, value in DEFAULT_CONTENT_BLOCKS:
        if db.query(ContentBlock).filter(ContentBlock.key == key).first() is None:
            db.add(ContentBlock(key=key, label=label, value=value, content_type="text"))

    for group_key, items in DEFAULT_REPEATABLE_ITEMS.items():
        if db.query(RepeatableItem).filter(RepeatableItem.group_key == group_key).count() == 0:
            for order, fields in enumerate(items):
                db.add(RepeatableItem(
                    group_key=group_key,
                    fields=json.dumps(fields, ensure_ascii=False),
                    display_order=order,
                    is_published=True,
                ))
            logger.info("Items par défaut insérés pour le groupe '%s' (%d).", group_key, len(items))

    db.commit()
