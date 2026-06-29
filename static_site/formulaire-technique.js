// ===========================================================
// CYBER TECK Q — Formulaire technique (formulaire-technique.html)
// ===========================================================

async function initTechnicalForm() {
  const guard = document.getElementById('tf-guard');
  const content = document.getElementById('tf-content');
  const guardTitle = document.getElementById('tf-guard-title');
  const guardText = document.getElementById('tf-guard-text');

  const params = new URLSearchParams(window.location.search);
  const orderId = params.get('order');

  if (!orderId) {
    guard.hidden = false;
    guardTitle.textContent = 'Commande introuvable';
    guardText.textContent = 'Aucune commande n\'a été spécifiée. Retournez à votre tableau de bord pour choisir une commande.';
    return;
  }

  // Vérifie que l'utilisateur est connecté et que la commande lui appartient
  let order;
  try {
    await Api.getMyProfile();
    order = await Api.getOrder(orderId);
  } catch (err) {
    guard.hidden = false;
    guardTitle.textContent = 'Accès refusé';
    guardText.textContent = 'Vous devez être connecté pour accéder à cette commande.';
    return;
  }

  // Le questionnaire technique ne s'applique pas aux contrats de maintenance :
  // redirige automatiquement vers la page du contrat de maintenance.
  if (order.product_type === 'maintenance') {
    window.location.href = `contrat-maintenance.html?order=${orderId}`;
    return;
  }

  if (order.has_technical_form) {
    guard.hidden = false;
    guardTitle.textContent = 'Questionnaire déjà soumis';
    guardText.textContent = `Le questionnaire technique pour la commande ${order.order_number} a déjà été envoyé. Notre équipe l'a bien reçu.`;
    return;
  }

  document.getElementById('tf-order-label').textContent = `${order.order_number} — ${order.product_name}`;
  content.hidden = false;

  const form = document.getElementById('technical-form');
  setupHostingConditionals(form);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFormMessage(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    const restore = setButtonLoading(submitBtn, 'Envoi en cours…');

    const data = new FormData(form);
    const payload = {};
    for (const [key, value] of data.entries()) {
      payload[key] = value;
    }
    // Les checkboxes non cochées n'apparaissent pas dans FormData : on les force à false
    ['has_existing_logo', 'has_images', 'feature_booking', 'feature_payment', 'feature_blog', 'feature_gallery', 'feature_shop']
      .forEach(key => { payload[key] = form.querySelector(`[name="${key}"]`).checked; });

    // Conversion des groupes radio Oui/Non en booléens (true/false), undefined si rien n'est cliqué
    ['has_current_hosting', 'wants_new_hosting', 'has_domain_name', 'wants_domain_help', 'wants_website_transfer']
      .forEach(key => {
        const checked = form.querySelector(`[name="${key}"]:checked`);
        payload[key] = checked ? checked.value === 'yes' : null;
      });

    // Champs legacy (hosting / domain_name) conservés pour compatibilité avec l'affichage admin existant
    if (payload.has_current_hosting && payload.hosting_provider) {
      payload.hosting = payload.hosting_provider;
    }

    try {
      await Api.submitTechnicalForm(orderId, payload);
      showFormMessage(form, 'Questionnaire envoyé avec succès ! Le paiement est maintenant débloqué. Redirection…', 'success');
      redirectAfter('mon-compte.html', 1800);
    } catch (err) {
      showFormMessage(form, err.message);
      restore();
    }
  });
}

/**
 * Gère l'affichage conditionnel des champs de la section Hébergement Web :
 * - "Avez-vous un hébergement actuel ?" -> Oui affiche fournisseur/accès
 * - "Possédez-vous déjà un nom de domaine ?" -> Oui affiche le champ nom de domaine
 */
function setupHostingConditionals(form) {
  const hostingRadios = form.querySelectorAll('[name="has_current_hosting"]');
  const hostingDetails = document.getElementById('tf-hosting-details');
  const toggleHostingDetails = () => {
    const checked = form.querySelector('[name="has_current_hosting"]:checked');
    hostingDetails.hidden = !(checked && checked.value === 'yes');
  };
  hostingRadios.forEach(r => r.addEventListener('change', toggleHostingDetails));
  toggleHostingDetails();

  const domainRadios = form.querySelectorAll('[name="has_domain_name"]');
  const domainField = document.getElementById('tf-domain-name-field');
  const toggleDomainField = () => {
    const checked = form.querySelector('[name="has_domain_name"]:checked');
    domainField.hidden = !(checked && checked.value === 'yes');
  };
  domainRadios.forEach(r => r.addEventListener('change', toggleDomainField));
  toggleDomainField();
}

document.addEventListener('DOMContentLoaded', initTechnicalForm);
