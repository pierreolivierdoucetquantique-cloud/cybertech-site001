// ===========================================================
// CYBER TECK Q — Formulaire technique (formulaire-technique.html)
// v9.11 : un questionnaire par OrderItem (service), pas par commande entière.
// ===========================================================

async function initTechnicalForm() {
  const guard = document.getElementById('tf-guard');
  const content = document.getElementById('tf-content');
  const guardTitle = document.getElementById('tf-guard-title');
  const guardText = document.getElementById('tf-guard-text');

  const params = new URLSearchParams(window.location.search);
  // "item" est le paramètre courant (v9.11). "order" est conservé en repli :
  // s'il pointe vers un panier à un seul service, on le résout automatiquement.
  let itemId = params.get('item');
  const legacyOrderId = params.get('order');

  if (!itemId && !legacyOrderId) {
    guard.hidden = false;
    guardTitle.textContent = 'Service introuvable';
    guardText.textContent = 'Aucun service n\'a été spécifié. Retournez à votre tableau de bord pour choisir une commande.';
    return;
  }

  // Vérifie que l'utilisateur est connecté
  try {
    await Api.getMyProfile();
  } catch (err) {
    guard.hidden = false;
    guardTitle.textContent = 'Accès refusé';
    guardText.textContent = 'Vous devez être connecté pour accéder à cette commande.';
    return;
  }

  let order, item;
  try {
    if (legacyOrderId && !itemId) {
      order = await Api.getOrder(legacyOrderId);
      if (order.items.length !== 1) {
        // Panier à plusieurs services : on ne peut pas deviner lequel, retour au tableau de bord
        window.location.href = 'mon-compte.html';
        return;
      }
      item = order.items[0];
      itemId = item.id;
    } else {
      // On ne connaît pas l'order_id à l'avance : on cherche l'item dans toutes les commandes du client.
      const myOrders = await Api.getMyOrders();
      for (const o of myOrders) {
        const found = o.items.find(i => i.id === itemId);
        if (found) { order = o; item = found; break; }
      }
      if (!item) throw new Error('Service introuvable.');
    }
  } catch (err) {
    guard.hidden = false;
    guardTitle.textContent = 'Service introuvable';
    guardText.textContent = 'Ce service est introuvable ou ne vous appartient pas.';
    return;
  }

  // Le questionnaire technique ne s'applique pas aux contrats de maintenance :
  // redirige automatiquement vers la page du contrat de maintenance.
  if (item.product_type === 'maintenance') {
    window.location.href = `contrat-maintenance.html?item=${itemId}`;
    return;
  }

  if (item.has_technical_form) {
    guard.hidden = false;
    guardTitle.textContent = 'Questionnaire déjà soumis';
    guardText.textContent = `Le questionnaire technique pour « ${item.product_name} » (commande ${order.order_number}) a déjà été envoyé. Notre équipe l'a bien reçu.`;
    return;
  }

  document.getElementById('tf-order-label').textContent = `${order.order_number} — ${item.product_name}`;
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
      await Api.submitTechnicalForm(itemId, payload);
      showFormMessage(form, 'Questionnaire envoyé avec succès ! Redirection…', 'success');
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
