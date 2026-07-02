// ===========================================================
// CYBER TECK Q — Configuration de l'éditeur de pages (CMS)
// ===========================================================
// Ce fichier décrit, pour chaque page publique, la liste des blocs de
// texte (ContentBlock) et des groupes d'items répétables (RepeatableItem)
// à afficher dans l'éditeur admin. Ajouter un nouveau champ éditable au
// site = ajouter une ligne ici, sans toucher au moteur de rendu.

const CMS_PAGE_SCHEMAS = {

  home: {
    label: 'Accueil',
    icon: 'home',
    blocks: [
      { key: 'home.hero.line1', label: 'Hero — ligne 1', type: 'text' },
      { key: 'home.hero.line2_prefix', label: 'Hero — ligne 2 (avant les mots animés)', type: 'text' },
      { key: 'home.hero.line3', label: 'Hero — ligne 3', type: 'text' },
      { key: 'home.hero.subtitle', label: 'Hero — sous-titre', type: 'textarea' },
      { key: 'home.hero.button_text', label: 'Hero — texte du bouton', type: 'text' },
      { key: 'home.hero.button_link', label: 'Hero — lien du bouton', type: 'text' },

      { key: 'home.story.eyebrow', label: 'Histoire — eyebrow', type: 'text' },
      { key: 'home.story.title', label: 'Histoire — titre', type: 'text' },
      { key: 'home.story.subtitle', label: 'Histoire — sous-titre', type: 'text' },
      { key: 'home.story.quote_text', label: 'Histoire — citation', type: 'textarea' },
      { key: 'home.story.quote_followup', label: 'Histoire — texte après la citation (HTML simple autorisé)', type: 'textarea' },

      { key: 'home.mission.eyebrow', label: 'Mission — eyebrow', type: 'text' },
      { key: 'home.mission.title', label: 'Mission — titre', type: 'text' },
      { key: 'home.mission.lead', label: 'Mission — texte d\'intro', type: 'textarea' },
      { key: 'home.mission.paragraph2', label: 'Mission — paragraphe 2', type: 'textarea' },
      { key: 'home.mission.paragraph3', label: 'Mission — paragraphe 3', type: 'textarea' },
      { key: 'home.mission.closing', label: 'Mission — phrase de clôture', type: 'text' },

      { key: 'home.portfolio.eyebrow', label: 'Réalisations — eyebrow', type: 'text' },
      { key: 'home.portfolio.title', label: 'Réalisations — titre', type: 'text' },
      { key: 'home.portfolio.subtitle', label: 'Réalisations — sous-titre', type: 'textarea' },
      { key: 'home.portfolio.cta_text', label: 'Réalisations — texte du bouton', type: 'text' },
      { key: 'home.portfolio.cta_link', label: 'Réalisations — lien du bouton', type: 'text' },
    ],
    groups: [
      {
        key: 'home.hero.typed_words',
        label: 'Mots animés du Hero',
        fields: [{ name: 'word', label: 'Mot', type: 'text' }],
        emptyFields: { word: '' },
      },
      {
        key: 'home.story.steps',
        label: 'Étapes de "Notre histoire"',
        fields: [
          { name: 'tag', label: 'Titre court', type: 'text' },
          { name: 'icon', label: 'Icône', type: 'icon' },
          { name: 'text', label: 'Texte', type: 'textarea' },
          { name: 'is_quote', label: 'Cette étape affiche la citation (au lieu du texte)', type: 'checkbox' },
        ],
        emptyFields: { tag: '', icon: 'star', text: '', is_quote: false },
      },
      {
        key: 'home.mission.values',
        label: 'Valeurs (Mission)',
        fields: [
          { name: 'text', label: 'Texte', type: 'text' },
          { name: 'icon', label: 'Icône', type: 'icon' },
        ],
        emptyFields: { text: '', icon: 'star' },
      },
      {
        key: 'home.trust_items',
        label: 'Barre de confiance',
        fields: [
          { name: 'text', label: 'Texte (un <br> est autorisé pour le saut de ligne)', type: 'text' },
          { name: 'icon', label: 'Icône', type: 'icon' },
        ],
        emptyFields: { text: '', icon: 'star' },
      },
    ],
  },

  services: {
    label: 'Services',
    icon: 'rocket',
    blocks: [
      { key: 'services.hero.eyebrow', label: 'Hero — eyebrow', type: 'text' },
      { key: 'services.hero.title', label: 'Hero — titre', type: 'text' },
      { key: 'services.hero.subtitle', label: 'Hero — sous-titre', type: 'textarea' },
      { key: 'services.process.eyebrow', label: 'Processus — eyebrow', type: 'text' },
      { key: 'services.process.title', label: 'Processus — titre', type: 'text' },
      { key: 'services.cta.title', label: 'CTA final — titre', type: 'text' },
      { key: 'services.cta.text', label: 'CTA final — texte', type: 'text' },
      { key: 'services.cta.button_text', label: 'CTA final — texte du bouton', type: 'text' },
      { key: 'services.cta.button_link', label: 'CTA final — lien du bouton', type: 'text' },
    ],
    groups: [
      {
        key: 'services.cards',
        label: 'Cartes de service',
        fields: [
          { name: 'title', label: 'Titre', type: 'text' },
          { name: 'icon', label: 'Icône', type: 'icon' },
          { name: 'text', label: 'Texte', type: 'textarea' },
          { name: 'features', label: 'Liste de caractéristiques (une par ligne)', type: 'list' },
          { name: 'button_text', label: 'Texte du bouton', type: 'text' },
          { name: 'button_link', label: 'Lien du bouton', type: 'text' },
        ],
        emptyFields: { title: '', icon: 'rocket', text: '', features: [], button_text: 'En savoir plus', button_link: 'contact.html' },
      },
      {
        key: 'services.process_steps',
        label: 'Étapes du processus',
        fields: [
          { name: 'number', label: 'Numéro (ex: 01)', type: 'text' },
          { name: 'title', label: 'Titre', type: 'text' },
          { name: 'text', label: 'Texte', type: 'textarea' },
        ],
        emptyFields: { number: '', title: '', text: '' },
      },
    ],
  },

  tarifs: {
    label: 'Tarifs',
    icon: 'tag',
    blocks: [
      { key: 'tarifs.hero.eyebrow', label: 'Hero — eyebrow', type: 'text' },
      { key: 'tarifs.hero.title', label: 'Hero — titre', type: 'text' },
      { key: 'tarifs.hero.subtitle', label: 'Hero — sous-titre', type: 'textarea' },
      { key: 'tarifs.note', label: 'Note sous les forfaits', type: 'textarea' },
      { key: 'tarifs.conditions.title', label: 'Titre — conditions de paiement', type: 'text' },
      { key: 'tarifs.cta.title', label: 'CTA final — titre', type: 'text' },
      { key: 'tarifs.cta.text', label: 'CTA final — texte', type: 'text' },
      { key: 'tarifs.cta.button_text', label: 'CTA final — texte du bouton', type: 'text' },
      { key: 'tarifs.cta.button_link', label: 'CTA final — lien du bouton', type: 'text' },
    ],
    groups: [
      {
        key: 'tarifs.conditions_items',
        label: 'Conditions de paiement (liste)',
        fields: [{ name: 'text', label: 'Texte', type: 'text' }],
        emptyFields: { text: '' },
      },
    ],
    note: 'Les forfaits (prix, fonctionnalités) se gèrent dans la section "Forfaits tarifaires" ci-dessus, pas ici.',
  },

  creation: {
    label: 'Création de votre site Web',
    icon: 'compass',
    blocks: [
      { key: 'creation.hero.eyebrow', label: 'Hero — eyebrow', type: 'text' },
      { key: 'creation.hero.title', label: 'Hero — titre', type: 'text' },
      { key: 'creation.hero.subtitle', label: 'Hero — sous-titre', type: 'textarea' },
      { key: 'creation.section.subtitle', label: 'Sous-titre de la section espace client', type: 'textarea' },
    ],
    groups: [],
  },

  faq_page: {
    label: 'FAQ (en-tête de page)',
    icon: 'quote',
    blocks: [
      { key: 'faq.hero.eyebrow', label: 'Hero — eyebrow', type: 'text' },
      { key: 'faq.hero.title', label: 'Hero — titre', type: 'text' },
      { key: 'faq.hero.subtitle', label: 'Hero — sous-titre', type: 'textarea' },
      { key: 'faq.cta.button_text', label: 'Bouton final — texte', type: 'text' },
      { key: 'faq.cta.button_link', label: 'Bouton final — lien', type: 'text' },
    ],
    groups: [],
    note: 'Les questions/réponses elles-mêmes se gèrent dans la section "FAQ" ci-dessus, pas ici.',
  },

  contact_page: {
    label: 'Contact (en-tête de page)',
    icon: 'support',
    blocks: [
      { key: 'contact.hero.eyebrow', label: 'Hero — eyebrow', type: 'text' },
      { key: 'contact.hero.title', label: 'Hero — titre', type: 'text' },
      { key: 'contact.hero.subtitle', label: 'Hero — sous-titre', type: 'textarea' },
      { key: 'contact.alt.eyebrow', label: '"Aussi par courriel" — eyebrow', type: 'text' },
    ],
    groups: [],
    note: 'Le courriel, téléphone, adresse et réseaux sociaux se gèrent dans la section "Coordonnées de contact" ci-dessus, pas ici.',
  },

  nav_footer: {
    label: 'Navigation & pied de page',
    icon: 'gear',
    blocks: [
      { key: 'nav.link_accueil', label: 'Lien menu — Accueil', type: 'text' },
      { key: 'nav.link_services', label: 'Lien menu — Services', type: 'text' },
      { key: 'nav.link_tarifs', label: 'Lien menu — Tarifs', type: 'text' },
      { key: 'nav.link_creation', label: 'Lien menu — Création de votre site Web', type: 'text' },
      { key: 'nav.link_faq', label: 'Lien menu — FAQ', type: 'text' },
      { key: 'nav.link_contact', label: 'Lien menu — Contact', type: 'text' },
      { key: 'footer.tagline', label: 'Pied de page — slogan', type: 'text' },
      { key: 'footer.copyright', label: 'Pied de page — texte de copyright (après l\'année)', type: 'text' },
    ],
    groups: [],
  },
};

// Icônes disponibles pour les champs de type "icon" (doit correspondre à
// CMS_ICONS côté site public, dans script.js)
const CMS_ICON_OPTIONS = [
  'rocket', 'shield', 'automation', 'support', 'star', 'gear',
  'clock', 'device', 'search', 'people', 'compass', 'quote',
];
