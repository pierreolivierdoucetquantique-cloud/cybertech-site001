// ===========================================================
// CYBER TECK Q — Utilitaires UI pour formulaires
// Affichage de messages d'erreur/succès inline, gestion des
// états de chargement sur les boutons.
// ===========================================================

/**
 * Affiche un message inline juste avant le bouton submit d'un formulaire.
 * Crée l'élément s'il n'existe pas encore, le réutilise sinon.
 */
function showFormMessage(form, message, type = 'error') {
  let el = form.querySelector('.form-message');
  if (!el) {
    el = document.createElement('p');
    el.className = 'form-message';
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.parentNode.insertBefore(el, submitBtn);
    } else {
      form.appendChild(el);
    }
  }
  el.textContent = message;
  el.classList.remove('form-message-error', 'form-message-success');
  el.classList.add(type === 'success' ? 'form-message-success' : 'form-message-error');
  el.hidden = false;
}

function clearFormMessage(form) {
  const el = form.querySelector('.form-message');
  if (el) el.hidden = true;
}

/**
 * Bascule un bouton submit en état "chargement" (désactivé + texte temporaire).
 * Retourne une fonction à appeler pour restaurer l'état initial.
 */
function setButtonLoading(button, loadingText = 'Veuillez patienter…') {
  if (!button) return () => {};
  const originalText = button.textContent;
  const originalDisabled = button.disabled;
  button.disabled = true;
  button.dataset.originalText = originalText;
  button.textContent = loadingText;
  return () => {
    button.disabled = originalDisabled;
    button.textContent = button.dataset.originalText || originalText;
  };
}

/**
 * Redirige vers une page après un court délai (laisse le temps de lire un message).
 */
function redirectAfter(url, delayMs = 900) {
  setTimeout(() => { window.location.href = url; }, delayMs);
}

/**
 * Échappe les caractères HTML spéciaux pour insérer du texte dynamique
 * en toute sécurité dans innerHTML (protection XSS de base).
 */
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ===========================================================
// CMS générique : applique les ContentBlock (textes) au DOM via des
// attributs data-cms-*, sans avoir à écrire du JS dédié pour chaque champ.
//
// Marquage HTML attendu :
//   <h1 data-cms-text="home.hero.title">Texte par défaut</h1>     -> textContent
//   <p data-cms-html="home.mission.lead">...</p>                  -> innerHTML (autorise <br>, <em>, etc. déjà présents dans le texte par défaut)
//   <a data-cms-href="home.hero.button_link" href="services.html"> -> attribut href
//
// Le texte par défaut déjà présent dans le HTML reste affiché tel quel si
// l'appel réseau échoue ou si la clé n'existe pas encore en base — aucune
// page ne se vide jamais à cause d'une erreur réseau.
// ===========================================================
async function applyCmsContentBlocks() {
  const textEls = document.querySelectorAll('[data-cms-text]');
  const htmlEls = document.querySelectorAll('[data-cms-html]');
  const hrefEls = document.querySelectorAll('[data-cms-href]');
  if (textEls.length === 0 && htmlEls.length === 0 && hrefEls.length === 0) return;

  try {
    const blocks = await Api.getPublicContentBlocks();
    const byKey = Object.fromEntries(blocks.map(b => [b.key, b.value]));

    textEls.forEach(el => {
      const key = el.dataset.cmsText;
      if (byKey[key]) el.textContent = byKey[key];
    });
    htmlEls.forEach(el => {
      const key = el.dataset.cmsHtml;
      if (byKey[key]) el.innerHTML = byKey[key];
    });
    hrefEls.forEach(el => {
      const key = el.dataset.cmsHref;
      if (byKey[key]) el.setAttribute('href', byKey[key]);
    });
  } catch (err) {
    // Erreur réseau : on garde silencieusement les textes par défaut du HTML.
  }
}

// ===========================================================
// CMS générique : charge des groupes d'items répétables (RepeatableItem)
// et appelle un "renderer" fourni par la page pour chaque groupe trouvé.
//
// Usage typique sur une page :
//   loadCmsRepeatableGroups({
//     'home.story.steps': renderStorySteps,
//     'home.mission.values': renderMissionValues,
//   });
//
// Si l'appel réseau échoue ou qu'un groupe n'a aucun item publié, le
// renderer n'est PAS appelé pour ce groupe — le contenu par défaut déjà
// présent dans le HTML reste affiché tel quel.
// ===========================================================
async function loadCmsRepeatableGroups(renderersByGroup) {
  const groupKeys = Object.keys(renderersByGroup);
  if (groupKeys.length === 0) return;
  try {
    const data = await Api.getPublicRepeatableItemsBulk(groupKeys);
    for (const key of groupKeys) {
      const items = data[key];
      if (items && items.length > 0) {
        renderersByGroup[key](items);
      }
    }
  } catch (err) {
    // Erreur réseau : on garde silencieusement le contenu par défaut du HTML.
  }
}
