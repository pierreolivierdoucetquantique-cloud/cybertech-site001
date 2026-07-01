// ===========================================================
// CYBERTECH QUANTUM — interactions & background animation
// ===========================================================

document.getElementById('year').textContent = new Date().getFullYear();

/* ---------- CMS : table d'icônes réutilisables pour les listes éditables ---------- */
const CMS_ICONS = {
  people: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="9" cy="7" r="3.2"/><path d="M3 20c0-3.3 2.7-5.6 6-5.6s6 2.3 6 5.6"/><circle cx="17" cy="8" r="2.4"/><path d="M14.2 14.8c2.3.2 4.8 1.9 4.8 5.2"/></svg>',
  compass: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><circle cx="12" cy="12" r="4.2"/></svg>',
  quote: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M9.5 7.5C7 7.5 5 9.5 5 12v5h5v-5H7.2c.1-1.4 1.1-2.5 2.3-2.5V7.5zm9 0c-2.5 0-4.5 2-4.5 4.5v5h5v-5h-2.8c.1-1.4 1.1-2.5 2.3-2.5V7.5z"/></svg>',
  rocket: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2c2.5 2.5 4 6 4 10l-4 4-4-4c0-4 1.5-7.5 4-10z"/><path d="M9 16l-3 5 5-3M15 16l3 5-5-3"/><circle cx="12" cy="9" r="1.4" fill="currentColor"/></svg>',
  star: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2.5l2.9 6 6.6.9-4.8 4.6 1.1 6.6L12 17.6l-5.8 3 1.1-6.6L2.5 9.4l6.6-.9L12 2.5z"/></svg>',
  gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 13a7.4 7.4 0 0 0 0-2l2-1.6-2-3.4-2.4.8a7.5 7.5 0 0 0-1.7-1l-.3-2.5h-4l-.3 2.5a7.5 7.5 0 0 0-1.7 1l-2.4-.8-2 3.4 2 1.6a7.4 7.4 0 0 0 0 2l-2 1.6 2 3.4 2.4-.8a7.5 7.5 0 0 0 1.7 1l.3 2.5h4l.3-2.5a7.5 7.5 0 0 0 1.7-1l2.4.8 2-3.4-2-1.6z"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2.5l7.5 3.2v6c0 5-3.3 8.3-7.5 9.8-4.2-1.5-7.5-4.8-7.5-9.8v-6L12 2.5z"/><path d="M8.7 12.2l2.3 2.3 4.3-4.7"/></svg>',
  device: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="6" y="2.5" width="12" height="19" rx="2"/><path d="M11 18.5h2"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>',
  support: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 13a9 9 0 0118 0"/><rect x="3" y="13" width="4" height="6" rx="1.2"/><rect x="17" y="13" width="4" height="6" rx="1.2"/></svg>',
  automation: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="5" y="2.5" width="14" height="19" rx="2.5"/><path d="M9 19h6"/></svg>',
};
function cmsIcon(key) { return CMS_ICONS[key] || CMS_ICONS.star; }

/* ---------- CMS : rendu des étapes de "Notre histoire" ---------- */
function renderStorySteps(items) {
  const container = document.getElementById('story-timeline');
  if (!container) return;
  container.innerHTML = items.map((item, i) => {
    const f = item.fields;
    const delay = `${i * 120}ms`;
    if (f.is_quote) {
      // La citation elle-même vit dans des ContentBlock globaux
      // (home.story.quote_text / quote_followup), déjà appliqués par
      // applyCmsContentBlocks() au chargement de la page — on les insère
      // ici avec des marqueurs data-cms-* pour qu'ils restent à jour même
      // si ce bloc est régénéré après coup.
      return `
        <div class="story-step story-step-quote" style="--reveal-delay:${delay}">
          <div class="story-step-icon">${cmsIcon(f.icon)}</div>
          <div class="story-step-content">
            <span class="story-step-tag">${escapeHtml(f.tag || '')}</span>
            <blockquote class="story-quote" data-cms-text="home.story.quote_text">« Le site web que tu construiras sera la limite de ton imagination. »</blockquote>
            <p data-cms-html="home.story.quote_followup">À cet instant, une seule pensée m'est venue : <em>« Mon imagination n'a aucune limite. »</em> C'est ainsi que l'aventure a commencé.</p>
          </div>
        </div>`;
    }
    return `
      <div class="story-step" style="--reveal-delay:${delay}">
        <div class="story-step-icon">${cmsIcon(f.icon)}</div>
        <div class="story-step-content">
          <span class="story-step-tag">${escapeHtml(f.tag || '')}</span>
          <p>${escapeHtml(f.text || '')}</p>
        </div>
      </div>`;
  }).join('');
  // Comme ce bloc vient d'être (re)généré après le premier passage de
  // applyCmsContentBlocks(), on la rappelle pour appliquer la citation aux
  // nouveaux éléments data-cms-* qui viennent d'apparaître dans le DOM.
  applyCmsContentBlocks();
}

/* ---------- CMS : rendu des valeurs de la Mission ---------- */
function renderMissionValues(items) {
  const container = document.getElementById('mission-values');
  if (!container) return;
  container.innerHTML = items.map(item => `
    <div class="story-value">
      ${cmsIcon(item.fields.icon)}
      <span>${escapeHtml(item.fields.text || '')}</span>
    </div>
  `).join('');
}

/* ---------- CMS : rendu de la barre de confiance ---------- */
function renderTrustItems(items) {
  const container = document.getElementById('trust-bar-items');
  if (!container) return;
  container.innerHTML = items.map(item => `
    <div class="trust-item">
      ${cmsIcon(item.fields.icon)}
      <span>${item.fields.text || ''}</span>
    </div>
  `).join('');
}

/* ---------- CMS : rendu des cartes de service ---------- */
function renderServiceCards(items) {
  const container = document.getElementById('services-cards-grid');
  if (!container) return;
  const iconClass = { rocket: 'icon-rocket', shield: 'icon-shield', automation: 'icon-automation', support: 'icon-support' };
  container.innerHTML = items.map(item => {
    const f = item.fields;
    const features = Array.isArray(f.features) ? f.features : [];
    return `
      <article class="service-card-full">
        <div class="card-icon ${iconClass[f.icon] || 'icon-rocket'}">${cmsIcon(f.icon)}</div>
        <h3>${escapeHtml(f.title || '')}</h3>
        <p>${escapeHtml(f.text || '')}</p>
        <ul class="card-list">
          ${features.map(feat => `<li>${escapeHtml(feat)}</li>`).join('')}
        </ul>
        <a href="${escapeHtml(f.button_link || 'contact.html')}" class="btn btn-outline">${escapeHtml(f.button_text || 'En savoir plus')}</a>
      </article>
    `;
  }).join('');
}

/* ---------- CMS : rendu des étapes du processus (services.html) ---------- */
function renderProcessSteps(items) {
  const container = document.getElementById('services-process-grid');
  if (!container) return;
  container.innerHTML = items.map(item => {
    const f = item.fields;
    return `
      <div class="process-step">
        <span class="step-num">${escapeHtml(f.number || '')}</span>
        <h4>${escapeHtml(f.title || '')}</h4>
        <p>${escapeHtml(f.text || '')}</p>
      </div>
    `;
  }).join('');
}

/* ---------- CMS : rendu des conditions de paiement (tarifs.html) ---------- */
function renderPaymentConditions(items) {
  const container = document.getElementById('tarifs-conditions-list');
  if (!container) return;
  container.innerHTML = items.map(item => `<li>${item.fields.text || ''}</li>`).join('');
}



/* ---------- CMS générique : textes/liens marqués data-cms-* ---------- */
applyCmsContentBlocks();

// Cas spécial : le préfixe de la ligne 2 du hero contient une animation
// imbriquée, donc on l'applique manuellement plutôt que via data-cms-text.
(async function applyHeroLine2Prefix() {
  const el = document.getElementById('hero-line2-prefix');
  if (!el) return;
  try {
    const blocks = await Api.getPublicContentBlocks();
    const block = blocks.find(b => b.key === 'home.hero.line2_prefix');
    if (block && block.value) el.textContent = block.value;
  } catch (err) {
    // Erreur réseau : garder le texte par défaut.
  }
})();


/* ---------- Adapter le lien "Création de votre site Web" selon l'état de connexion ---------- */
(async function adaptAuthNavLink() {
  const link = document.querySelector('.nav-link-cta-text');
  if (!link) return;

  // Applique d'abord le texte CMS par défaut (si personnalisé), avant de
  // vérifier l'état de connexion — cette fonction reste la seule à modifier
  // le nœud texte de ce lien pour éviter tout conflit/doublon.
  let defaultText = 'Création de votre site Web';
  try {
    const blocks = await Api.getPublicContentBlocks();
    const block = blocks.find(b => b.key === 'nav.link_creation');
    if (block && block.value) defaultText = block.value;
  } catch (err) {
    // Erreur réseau : garder le texte par défaut codé en dur.
  }
  const textNode = [...link.childNodes].find(n => n.nodeType === Node.TEXT_NODE);
  if (textNode) textNode.textContent = defaultText;

  try {
    await Api.getMyProfile();
    // Connecté : ne change le lien que s'il pointe vers la page de connexion
    if (link.getAttribute('href') === 'creation-site-web.html') {
      link.setAttribute('href', 'mon-compte.html');
      const tn = [...link.childNodes].find(n => n.nodeType === Node.TEXT_NODE);
      if (tn) {
        tn.textContent = 'Mon espace client';
      } else {
        link.append('Mon espace client');
      }
    }
  } catch (err) {
    // Non connecté : laisser tel quel (mène vers la page de connexion/inscription)
  }
})();

/* ---------- Header scroll state + mobile nav ---------- */
const header = document.getElementById('site-header');
window.addEventListener('scroll', () => {
  header.classList.toggle('is-scrolled', window.scrollY > 12);
}, { passive: true });

const navToggle = document.getElementById('nav-toggle');
const mainNav = document.getElementById('main-nav');
navToggle.addEventListener('click', () => {
  const open = mainNav.classList.toggle('is-open');
  navToggle.setAttribute('aria-expanded', open);
});
mainNav.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
  mainNav.classList.remove('is-open');
  navToggle.setAttribute('aria-expanded', 'false');
}));

/* Active nav link on scroll */
const sections = ['accueil']
  .map(id => document.getElementById(id)).filter(Boolean);
const navLinks = document.querySelectorAll('.nav-link');
window.addEventListener('scroll', () => {
  let current = sections[0];
  sections.forEach(s => { if (window.scrollY + 140 >= s.offsetTop) current = s; });
  navLinks.forEach(l => l.classList.remove('is-active'));
  // Map first nav link to "accueil" hero only
}, { passive: true });

/* ---------- Typing effect (infinite loop) ---------- */
let typedWords = ['PROPULSENT', 'INSPIRENT', 'TRANSFORMENT', 'CONNECTENT'];
const typedEl = document.getElementById('typed-text');
let wordIndex = 0, charIndex = 0, deleting = false;

function typeLoop() {
  if (!typedEl) return;
  const word = typedWords[wordIndex] || '';
  if (!deleting) {
    charIndex++;
    typedEl.textContent = word.slice(0, charIndex);
    if (charIndex === word.length) {
      deleting = true;
      setTimeout(typeLoop, 1800);
      return;
    }
  } else {
    charIndex--;
    typedEl.textContent = word.slice(0, charIndex);
    if (charIndex === 0) {
      deleting = false;
      wordIndex = (wordIndex + 1) % typedWords.length;
    }
  }
  setTimeout(typeLoop, deleting ? 45 : 85);
}
typeLoop();

// Si le CMS contient des mots personnalisés, on remplace la liste et on
// redémarre l'animation proprement (sans à-coup visuel majeur).
if (document.getElementById('hero-line2-prefix')) {
  loadCmsRepeatableGroups({
    'home.hero.typed_words': (items) => {
      const words = items.map(i => i.fields.word).filter(Boolean);
      if (words.length > 0) {
        typedWords = words;
        wordIndex = 0; charIndex = 0; deleting = false;
      }
    },
  });
}

/* ---------- Reveal hero subtitle & CTA after the title settles in ---------- */
const heroSubtitle = document.querySelector('.hero-subtitle');
const heroCta = document.querySelector('.hero-cta');
window.setTimeout(() => {
  if (heroSubtitle) heroSubtitle.hidden = false;
  if (heroCta) heroCta.hidden = false;
}, 600);

/* ---------- FAQ accordion ---------- */
function bindFaqAccordion() {
  document.querySelectorAll('.faq-question').forEach(btn => {
    btn.addEventListener('click', () => {
      const item = btn.closest('.faq-item');
      const answer = item.querySelector('.faq-answer');
      const isOpen = btn.getAttribute('aria-expanded') === 'true';

      document.querySelectorAll('.faq-question').forEach(b => {
        b.setAttribute('aria-expanded', 'false');
        b.closest('.faq-item').querySelector('.faq-answer').style.maxHeight = null;
      });

      if (!isOpen) {
        btn.setAttribute('aria-expanded', 'true');
        answer.style.maxHeight = answer.scrollHeight + 'px';
      }
    });
  });
}
bindFaqAccordion();

/* ---------- Connexion / Création de compte ---------- */
const clientTabs = document.querySelectorAll('.client-tab');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');

// Si déjà connecté (client OU admin), rediriger directement vers le bon espace
// plutôt que d'afficher à nouveau le formulaire de connexion.
if (loginForm) {
  (async function checkAlreadyLoggedIn() {
    try {
      await Api.adminGetMyProfile();
      window.location.href = 'admin-dashboard.html';
      return;
    } catch (err) {
      // pas connecté en admin, on continue
    }
    try {
      await Api.getMyProfile();
      window.location.href = 'mon-compte.html';
    } catch (err) {
      // pas connecté du tout : rester sur la page de connexion
    }
  })();
}

clientTabs.forEach(tab => {
  tab.addEventListener('click', () => {
    clientTabs.forEach(t => t.classList.remove('is-active'));
    tab.classList.add('is-active');
    const isLogin = tab.dataset.tab === 'login';
    loginForm.hidden = !isLogin;
    registerForm.hidden = isLogin;
  });
});

/* ---------- Password visibility toggles ---------- */
document.querySelectorAll('.toggle-password').forEach(btn => {
  btn.addEventListener('click', () => {
    const input = document.getElementById(btn.dataset.target);
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
  });
});

/* ---------- Register form: realtime password match validation ---------- */
const regPassword = document.getElementById('register-password');
const confirmPassword = document.getElementById('confirm-password');
const matchError = document.getElementById('password-match-error');
function checkPasswordMatch() {
  if (!regPassword || !confirmPassword) return true;
  const mismatch = confirmPassword.value.length > 0 && confirmPassword.value !== regPassword.value;
  matchError.hidden = !mismatch;
  return !mismatch;
}
if (regPassword && confirmPassword) {
  regPassword.addEventListener('input', checkPasswordMatch);
  confirmPassword.addEventListener('input', checkPasswordMatch);
}

registerForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!checkPasswordMatch()) return;
  clearFormMessage(registerForm);

  const submitBtn = registerForm.querySelector('button[type="submit"]');
  const restore = setButtonLoading(submitBtn, 'Création en cours…');

  const formData = new FormData(registerForm);
  const payload = {
    first_name: formData.get('prenom'),
    last_name: formData.get('nom'),
    email: formData.get('courriel'),
    phone: formData.get('telephone') || null,
    password: formData.get('password'),
  };

  try {
    await Api.register(payload);
    showFormMessage(registerForm, 'Compte créé avec succès ! Redirection…', 'success');
    redirectAfter('mon-compte.html');
  } catch (err) {
    showFormMessage(registerForm, err.message);
    restore();
  }
});

loginForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearFormMessage(loginForm);

  const submitBtn = loginForm.querySelector('button[type="submit"]');
  const restore = setButtonLoading(submitBtn, 'Connexion…');

  const formData = new FormData(loginForm);
  const payload = {
    email: formData.get('email'),
    password: formData.get('password'),
  };

  // Essaie d'abord la connexion CLIENT (cas le plus fréquent).
  try {
    await Api.login(payload);
    showFormMessage(loginForm, 'Connexion réussie ! Redirection…', 'success');
    redirectAfter('mon-compte.html');
    return;
  } catch (clientErr) {
    // Si ce n'est pas un simple refus d'identifiants (ex: compte désactivé,
    // trop de tentatives), on affiche directement cette erreur-là plutôt
    // que de tenter la connexion admin.
    if (clientErr.status !== 401) {
      showFormMessage(loginForm, clientErr.message);
      restore();
      return;
    }
  }

  // Bascule silencieuse : ce n'est peut-être pas un compte client, mais un compte admin.
  try {
    await Api.adminLogin(payload);
    showFormMessage(loginForm, 'Connexion réussie ! Redirection vers l\'administration…', 'success');
    redirectAfter('admin-dashboard.html');
  } catch (adminErr) {
    // Si le compte admin est verrouillé ou trop de tentatives ont été faites,
    // ce message est important et ne doit pas être masqué.
    if (adminErr.status === 429 || adminErr.status === 403) {
      showFormMessage(loginForm, adminErr.message);
    } else {
      // Ni client ni admin avec un identifiant/mot de passe valide : message
      // générique, volontairement sans préciser lequel des deux a échoué.
      showFormMessage(loginForm, 'Courriel ou mot de passe invalide.');
    }
    restore();
  }
});

/* ---------- Mot de passe oublié ---------- */
const forgotLink = document.querySelector('.forgot-link');
forgotLink?.addEventListener('click', async (e) => {
  e.preventDefault();
  const emailInput = loginForm?.querySelector('input[name="email"]');
  const email = emailInput?.value?.trim();
  if (!email) {
    showFormMessage(loginForm, 'Entrez votre courriel ci-dessus, puis cliquez à nouveau sur ce lien.');
    emailInput?.focus();
    return;
  }
  try {
    const res = await Api.forgotPassword(email);
    showFormMessage(loginForm, res.message, 'success');
  } catch (err) {
    showFormMessage(loginForm, err.message);
  }
});

/* ---------- Contact form submission ---------- */
const contactForm = document.getElementById('contact-form');
const formSuccess = document.getElementById('form-success');
contactForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearFormMessage(contactForm);

  const submitBtn = contactForm.querySelector('button[type="submit"]');
  const restore = setButtonLoading(submitBtn, 'Envoi en cours…');

  const formData = new FormData(contactForm);
  const payload = {
    prenom: formData.get('prenom'),
    nom: formData.get('nom'),
    courriel: formData.get('courriel'),
    telephone: formData.get('telephone') || null,
    sujet: formData.get('sujet'),
    message: formData.get('message'),
  };

  try {
    await Api.sendContactMessage(payload);
    if (formSuccess) {
      formSuccess.hidden = false;
      setTimeout(() => { formSuccess.hidden = true; }, 5000);
    }
    contactForm.reset();
    restore();
  } catch (err) {
    showFormMessage(contactForm, err.message);
    restore();
  }
});

/* ---------------------------------------------------------
   BACKGROUND — image statique fixe en CSS (assets/cover-full.jpg),
   appliquée à toutes les pages du site via .bg-cover-layer
   --------------------------------------------------------- */

/* ---------- Tarifs dynamiques (CMS) ---------- */
(async function loadPublicPricing() {
  const grid = document.getElementById('pricing-grid');
  if (!grid) return; // pas sur la page tarifs.html

  try {
    const plans = await Api.getPublicPricing();
    if (!plans || plans.length === 0) return; // garder les cartes par défaut si le CMS est vide

    grid.innerHTML = plans.map(plan => `
      <article class="pricing-card${plan.is_featured ? ' pricing-card-featured' : ''}">
        ${plan.is_featured ? '<span class="pricing-badge">Populaire</span>' : ''}
        <h3>${escapeHtml(plan.name)}</h3>
        <div class="pricing-amount"><span class="pricing-value">${escapeHtml(plan.price)}</span></div>
        <ul class="pricing-features">
          ${plan.features.map(f => `<li>${escapeHtml(f)}</li>`).join('')}
        </ul>
        <a href="contact.html" class="btn ${plan.is_featured ? 'btn-gradient' : 'btn-outline'}">Demander une soumission</a>
      </article>
    `).join('');
  } catch (err) {
    // Erreur réseau/API : on garde silencieusement les cartes par défaut déjà dans le HTML.
  }
})();

/* ---------- Coordonnées de contact dynamiques (CMS) ---------- */
(async function loadPublicContactInfo() {
  try {
    const blocks = await Api.getPublicContentBlocks();
    const byKey = Object.fromEntries(blocks.map(b => [b.key, b.value]));

    // Email : présent dans le footer de toutes les pages
    if (byKey['contact.email']) {
      document.querySelectorAll('.footer-email').forEach(el => {
        el.textContent = byKey['contact.email'];
        el.href = `mailto:${byKey['contact.email']}`;
      });
    }

    // Téléphone / adresse / réseaux sociaux : affichés s'il existe des
    // emplacements dédiés sur la page (ex: contact.html). Sans effet sur les
    // pages qui n'ont pas ces éléments.
    const phoneEl = document.getElementById('contact-phone-display');
    if (phoneEl) {
      if (byKey['contact.phone']) { phoneEl.textContent = byKey['contact.phone']; phoneEl.closest('[data-contact-row]')?.removeAttribute('hidden'); }
      else { phoneEl.closest('[data-contact-row]')?.setAttribute('hidden', ''); }
    }
    const addressEl = document.getElementById('contact-address-display');
    if (addressEl) {
      if (byKey['contact.address']) { addressEl.textContent = byKey['contact.address']; addressEl.closest('[data-contact-row]')?.removeAttribute('hidden'); }
      else { addressEl.closest('[data-contact-row]')?.setAttribute('hidden', ''); }
    }
    const socialWrap = document.getElementById('contact-social-links');
    if (socialWrap) {
      const links = [
        ['Facebook', byKey['contact.social_facebook']],
        ['Instagram', byKey['contact.social_instagram']],
        ['LinkedIn', byKey['contact.social_linkedin']],
      ].filter(([, url]) => url);
      if (links.length > 0) {
        socialWrap.innerHTML = links.map(([label, url]) => `<a href="${url}" target="_blank" rel="noopener">${label}</a>`).join('');
        socialWrap.hidden = false;
      }
    }
  } catch (err) {
    // Erreur réseau/API : on garde silencieusement les coordonnées par défaut déjà dans le HTML.
  }
})();
(async function loadPublicFaq() {
  const list = document.getElementById('faq-list');
  if (!list) return; // pas de FAQ sur cette page

  try {
    const items = await Api.getPublicFaq();
    if (!items || items.length === 0) return; // garder la FAQ par défaut si le CMS est vide

    list.innerHTML = items.map(item => `
      <div class="faq-item">
        <button class="faq-question" aria-expanded="false">
          <span>${escapeHtml(item.question)}</span>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
        </button>
        <div class="faq-answer"><p>${escapeHtml(item.answer)}</p></div>
      </div>
    `).join('');

    bindFaqAccordion();
  } catch (err) {
    // Erreur réseau/API : on garde silencieusement la FAQ par défaut déjà dans le HTML.
  }
})();

/* ---------- CMS : listes répétables (selon les conteneurs présents sur la page) ---------- */
loadCmsRepeatableGroups({
  'home.story.steps': renderStorySteps,
  'home.mission.values': renderMissionValues,
  'home.trust_items': renderTrustItems,
  'services.cards': renderServiceCards,
  'services.process_steps': renderProcessSteps,
  'tarifs.conditions_items': renderPaymentConditions,
});

/* ---------- Portfolio dynamique (réalisations gérées en admin) ---------- */
(async function loadPublicPortfolio() {
  const grid = document.getElementById('portfolio-grid');
  if (!grid) return; // pas sur la page d'accueil

  try {
    const projects = await Api.getPortfolio();
    if (!projects || projects.length === 0) return; // garder la carte par défaut si aucune réalisation publiée

    grid.innerHTML = projects.map((p, i) => {
      const initials = (p.title || '??').split(/\s+/).map(w => w[0]).join('').slice(0, 2).toUpperCase();
      const media = p.preview_image_path
        ? `<img src="${escapeHtml(p.preview_image_path)}" alt="${escapeHtml(p.title)}" class="portfolio-card-img">`
        : `<span class="portfolio-card-badge">${escapeHtml(initials)}</span>`;
      const tags = (p.technologies || '').split(',').map(t => t.trim()).filter(Boolean);
      const link = p.external_link || '#';
      return `
        <article class="portfolio-card" style="--reveal-delay:${i * 80}ms">
          <a href="${escapeHtml(link)}" target="_blank" rel="noopener" class="portfolio-card-media">
            ${media}
            <span class="portfolio-card-overlay">
              Visiter le site
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4"><path d="M7 17L17 7M7 7h10v10"/></svg>
            </span>
          </a>
          <div class="portfolio-card-body">
            <h3>${escapeHtml(p.title)}</h3>
            <p>${escapeHtml(p.description || '')}</p>
            ${tags.length > 0 ? `<div class="portfolio-card-tags">${tags.map(t => `<span>${escapeHtml(t)}</span>`).join('')}</div>` : ''}
          </div>
        </article>
      `;
    }).join('');

    grid.classList.toggle('portfolio-grid-single', projects.length === 1);
  } catch (err) {
    // Erreur réseau/API : on garde silencieusement la réalisation par défaut déjà dans le HTML.
  }
})();


