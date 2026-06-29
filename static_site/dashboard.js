// ===========================================================
// CYBER TECK Q — Dashboard client (mon-compte.html)
// ===========================================================

const PRODUCT_LABELS = {
  website: 'Création de site Web',
  mobile_app: 'Application Mobile',
  maintenance: 'Contrat de Maintenance',
};
const STATUS_LABELS = {
  pending: 'En attente', processing: 'En cours', delivered: 'Livré',
  cancelled: 'Annulé', archived: 'Archivé',
};
const PAYMENT_LABELS = {
  unpaid: 'Non payé', deposit_paid: 'Dépôt reçu', paid: 'Payé', refunded: 'Remboursé',
};

let currentClient = null;

async function initDashboard() {
  const shell = document.getElementById('dashboard-shell');
  const guard = document.getElementById('dashboard-guard');

  try {
    currentClient = await Api.getMyProfile();
  } catch (err) {
    shell.hidden = true;
    guard.hidden = false;
    return;
  }

  guard.hidden = true;
  shell.hidden = false;
  renderUserCard(currentClient);
  fillProfileForm(currentClient);

  setupTabs();
  setupLogout();
  setupProfileForm();
  setupPasswordForm();
  setupDeleteAccount();
  setupDeleteOrderModal();
  setupPaymentPanel();

  await Promise.all([loadMarketplace(), loadOrders(), loadInvoices(), loadDocuments()]);
  handleStripeReturn();
}

function handleStripeReturn() {
  const params = new URLSearchParams(window.location.search);
  const stripeResult = params.get('stripe');
  if (!stripeResult) return;

  if (stripeResult === 'success') {
    alert('Merci ! Votre paiement est en cours de confirmation. Le statut de votre commande sera mis à jour dans quelques instants.');
  } else if (stripeResult === 'cancel') {
    alert('Le paiement a été annulé. Vous pouvez réessayer à tout moment depuis l\'onglet "Paiement".');
  }
  // Nettoie l'URL pour éviter de réafficher le message au rafraîchissement
  window.history.replaceState({}, '', 'mon-compte.html');
  document.querySelector('.dashboard-tab[data-panel="payment"]')?.click();
  populatePaymentOrderPicker();
}

function renderUserCard(client) {
  const initials = (client.first_name[0] || '') + (client.last_name[0] || '');
  document.getElementById('user-avatar').textContent = initials;
  document.getElementById('user-name').textContent = `${client.first_name} ${client.last_name}`;
  document.getElementById('user-email').textContent = client.email;
}

function fillProfileForm(client) {
  const form = document.getElementById('profile-form');
  if (!form) return;
  for (const field of ['first_name', 'last_name', 'phone', 'address', 'city', 'postal_code', 'country']) {
    const input = form.querySelector(`[name="${field}"]`);
    if (input) input.value = client[field] || '';
  }
}

/* ---------- Tabs ---------- */
function setupTabs() {
  const tabs = document.querySelectorAll('.dashboard-tab');
  const panels = document.querySelectorAll('.dashboard-panel');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('is-active'));
      panels.forEach(p => p.classList.remove('is-active'));
      tab.classList.add('is-active');
      document.querySelector(`.dashboard-panel[data-panel="${tab.dataset.panel}"]`)?.classList.add('is-active');
    });
  });
}

/* ---------- Logout ---------- */
function setupLogout() {
  document.getElementById('logout-btn')?.addEventListener('click', async () => {
    try { await Api.logout(); } catch (e) { /* on redirige quand même */ }
    window.location.href = 'index.html';
  });
}

/* ---------- Marketplace ---------- */
async function loadMarketplace() {
  const grid = document.getElementById('marketplace-grid');
  try {
    const products = await Api.getMarketplace();
    grid.innerHTML = products.map(p => `
      <div class="marketplace-card">
        <h3>${escapeHtml(p.name)}</h3>
        <p>${escapeHtml(p.description)}</p>
        <div class="marketplace-card-price">${p.price.toLocaleString('fr-CA')} $ ${escapeHtml(p.currency)}</div>
        <ul class="marketplace-card-features">
          ${p.features.map(f => `<li>${escapeHtml(f)}</li>`).join('')}
        </ul>
        <button class="btn btn-gradient order-btn" data-product="${p.product_type}" style="width:100%">Commander</button>
      </div>
    `).join('');

    grid.querySelectorAll('.order-btn').forEach(btn => {
      btn.addEventListener('click', () => placeOrder(btn));
    });
  } catch (err) {
    grid.innerHTML = `<p class="dashboard-empty">Impossible de charger le catalogue pour le moment.</p>`;
  }
}

async function placeOrder(button) {
  const productType = button.dataset.product;
  const restore = setButtonLoading(button, 'Commande en cours…');
  try {
    await Api.createOrder(productType);
    await Promise.all([loadOrders(), loadOverviewStats()]);
    document.querySelector('.dashboard-tab[data-panel="orders"]').click();
  } catch (err) {
    alert(err.message);
  } finally {
    restore();
  }
}

/* ---------- Orders ---------- */
let allOrders = [];

async function loadOrders() {
  const list = document.getElementById('orders-list');
  try {
    allOrders = await Api.getMyOrders();
    renderOrders();
    await loadOverviewStats();
  } catch (err) {
    list.innerHTML = `<p class="dashboard-empty">Impossible de charger vos commandes.</p>`;
  }
}

function renderOrders() {
  const list = document.getElementById('orders-list');
  if (allOrders.length === 0) {
    list.innerHTML = `<p class="dashboard-empty">Vous n'avez pas encore de commande. Choisissez un service dans le tableau de bord pour démarrer votre projet.</p>`;
    return;
  }
  list.innerHTML = allOrders.map(o => {
    const isMaintenance = o.product_type === 'maintenance';
    const lockedBanner = !o.payment_unlocked
      ? `<div class="payment-locked-banner">${isMaintenance ? 'Veuillez signer le contrat de maintenance avant de poursuivre votre commande.' : 'Veuillez compléter le questionnaire avant de poursuivre votre commande.'}</div>`
      : '';
    const actionHtml = isMaintenance
      ? (o.maintenance_contract_signed
          ? `<span class="status-badge status-delivered">Contrat signé</span>`
          : `<a href="contrat-maintenance.html?order=${o.id}" class="btn btn-outline">${o.has_maintenance_contract ? 'Compléter la signature' : 'Signer le contrat'}</a>`)
      : (o.has_technical_form
          ? `<span class="status-badge status-delivered">Questionnaire envoyé</span>`
          : `<a href="formulaire-technique.html?order=${o.id}" class="btn btn-outline">Remplir le questionnaire</a>`);
    return `
    <div class="order-card">
      <div class="order-card-main">
        <div class="order-card-number">${escapeHtml(o.order_number)}</div>
        <div class="order-card-product">${escapeHtml(o.product_name)}</div>
        <div class="order-card-price">${o.price.toLocaleString('fr-CA')} $ CAD</div>
        <div class="order-card-progress">
          <div class="order-progress-bar"><div class="order-progress-fill progress-${o.progress_color}" style="width:${o.project_progress}%"></div></div>
          <div class="order-progress-meta">
            <span><strong>${o.project_progress}%</strong></span>
            <span>Étape : <strong>${escapeHtml(o.progress_step_label)}</strong></span>
            <span>Mis à jour : <strong>${new Date(o.updated_at).toLocaleDateString('fr-CA')}</strong></span>
            ${o.expected_delivery_date ? `<span>Livraison prévue : <strong>${new Date(o.expected_delivery_date).toLocaleDateString('fr-CA')}</strong></span>` : ''}
          </div>
        </div>
        ${lockedBanner}
      </div>
      <div class="order-card-badges">
        <span class="status-badge status-${o.status}">${STATUS_LABELS[o.status] || o.status}</span>
        <span class="status-badge payment-${o.payment_status}">${PAYMENT_LABELS[o.payment_status] || o.payment_status}</span>
      </div>
      <div class="order-card-action">
        ${actionHtml}
        ${o.status === 'pending'
          ? `<button type="button" class="order-card-delete" data-action="delete-order" data-id="${o.id}">Supprimer</button>`
          : ''}
      </div>
    </div>
  `;
  }).join('');

  list.querySelectorAll('[data-action="delete-order"]').forEach(btn => {
    btn.addEventListener('click', () => openDeleteOrderModal(btn.dataset.id));
  });
}

/* ---------- Delete order (panier) ---------- */
let orderIdPendingDeletion = null;

function setupDeleteOrderModal() {
  const modal = document.getElementById('delete-order-modal');
  document.getElementById('cancel-delete-order').addEventListener('click', () => {
    modal.hidden = true;
    orderIdPendingDeletion = null;
  });
  document.getElementById('confirm-delete-order').addEventListener('click', async () => {
    if (!orderIdPendingDeletion) return;
    const btn = document.getElementById('confirm-delete-order');
    const restore = setButtonLoading(btn, 'Suppression…');
    try {
      await Api.deleteOrder(orderIdPendingDeletion);
      modal.hidden = true;
      orderIdPendingDeletion = null;
      await Promise.all([loadOrders(), loadOverviewStats()]);
    } catch (err) {
      alert(err.message);
    } finally {
      restore();
    }
  });
}

function openDeleteOrderModal(orderId) {
  orderIdPendingDeletion = orderId;
  document.getElementById('delete-order-modal').hidden = false;
}

async function loadOverviewStats() {
  const container = document.getElementById('overview-stats');
  const total = allOrders.length;
  const inProgress = allOrders.filter(o => o.status === 'processing').length;
  const delivered = allOrders.filter(o => o.status === 'delivered').length;
  container.innerHTML = `
    <div class="dashboard-stat-card"><div class="dashboard-stat-value">${total}</div><div class="dashboard-stat-label">Commande(s) au total</div></div>
    <div class="dashboard-stat-card"><div class="dashboard-stat-value">${inProgress}</div><div class="dashboard-stat-label">En cours de réalisation</div></div>
    <div class="dashboard-stat-card"><div class="dashboard-stat-value">${delivered}</div><div class="dashboard-stat-label">Projet(s) livré(s)</div></div>
  `;
}

/* ---------- Invoices ---------- */
async function loadInvoices() {
  const list = document.getElementById('invoices-list');
  try {
    const invoices = await Api.getMyInvoices();
    if (invoices.length === 0) {
      list.innerHTML = `<p class="dashboard-empty">Aucune facture pour le moment. Vos factures apparaîtront ici dès qu'un paiement sera confirmé.</p>`;
      return;
    }
    list.innerHTML = invoices.map(inv => `
      <div class="invoice-card">
        <div>
          <div class="invoice-card-number">${escapeHtml(inv.invoice_number)}</div>
          <div class="invoice-card-date">${new Date(inv.created_at).toLocaleDateString('fr-CA')}</div>
        </div>
        <div class="invoice-card-total">${inv.total.toLocaleString('fr-CA')} $ CAD</div>
        <a class="btn btn-outline" href="/api/invoices/${inv.id}/download" target="_blank" rel="noopener">Télécharger</a>
      </div>
    `).join('');
  } catch (err) {
    list.innerHTML = `<p class="dashboard-empty">Impossible de charger vos factures.</p>`;
  }
}

/* ---------- Profile form ---------- */
function setupProfileForm() {
  const form = document.getElementById('profile-form');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFormMessage(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    const restore = setButtonLoading(submitBtn, 'Enregistrement…');

    const data = new FormData(form);
    const payload = Object.fromEntries(data.entries());

    try {
      currentClient = await Api.updateMyProfile(payload);
      renderUserCard(currentClient);
      showFormMessage(form, 'Profil mis à jour avec succès.', 'success');
    } catch (err) {
      showFormMessage(form, err.message);
    } finally {
      restore();
    }
  });
}

/* ---------- Password form ---------- */
function setupPasswordForm() {
  const form = document.getElementById('password-form');
  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFormMessage(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    const restore = setButtonLoading(submitBtn, 'Mise à jour…');

    const data = new FormData(form);
    const payload = Object.fromEntries(data.entries());

    try {
      await Api.changeMyPassword(payload);
      showFormMessage(form, 'Mot de passe modifié. Redirection vers la connexion…', 'success');
      redirectAfter('creation-site-web.html', 1500);
    } catch (err) {
      showFormMessage(form, err.message);
      restore();
    }
  });
}

/* ---------- Delete account ---------- */
function setupDeleteAccount() {
  const modal = document.getElementById('delete-modal');
  const openBtn = document.getElementById('open-delete-modal');
  const cancelBtn = document.getElementById('cancel-delete');
  const form = document.getElementById('delete-account-form');

  openBtn?.addEventListener('click', () => { modal.hidden = false; });
  cancelBtn?.addEventListener('click', () => { modal.hidden = true; form.reset(); clearFormMessage(form); });

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFormMessage(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    const restore = setButtonLoading(submitBtn, 'Suppression…');

    const data = new FormData(form);
    const payload = Object.fromEntries(data.entries());

    try {
      await Api.deleteMyAccount(payload);
      window.location.href = 'compte-supprime.html';
    } catch (err) {
      showFormMessage(form, err.message);
      restore();
    }
  });
}

/* ---------- Paiement ---------- */
let interacInfo = null;
let currentPaymentOrderId = null;
let pendingInteracPaymentId = null;

function setupPaymentPanel() {
  document.getElementById('payment-order-picker').addEventListener('change', (e) => {
    onPaymentOrderSelected(e.target.value);
  });

  document.getElementById('interac-start-btn').addEventListener('click', startInteracPayment);
  document.getElementById('interac-upload-btn').addEventListener('click', uploadInteracProof);
  document.getElementById('stripe-checkout-btn').addEventListener('click', startStripeCheckout);

  // Tab "Paiement" : peupler le sélecteur de commandes à l'ouverture
  document.querySelector('.dashboard-tab[data-panel="payment"]').addEventListener('click', () => {
    populatePaymentOrderPicker();
  });
}

function populatePaymentOrderPicker() {
  const picker = document.getElementById('payment-order-picker');
  const payable = allOrders; // toutes les commandes peuvent être payées (dépôt ou solde)
  if (payable.length === 0) {
    picker.innerHTML = `<option value="">Aucune commande</option>`;
    document.getElementById('payment-methods').hidden = true;
    document.getElementById('payment-locked-notice').hidden = true;
    return;
  }
  const previousValue = picker.value;
  picker.innerHTML = payable.map(o => `<option value="${o.id}">${escapeHtml(o.order_number)} — ${escapeHtml(o.product_name)}</option>`).join('');
  const toSelect = payable.find(o => o.id === previousValue) ? previousValue : payable[0].id;
  picker.value = toSelect;
  onPaymentOrderSelected(toSelect);
}

async function onPaymentOrderSelected(orderId) {
  currentPaymentOrderId = orderId;
  const order = allOrders.find(o => o.id === orderId);
  if (!order) return;

  const locked = !order.payment_unlocked;
  const lockedNotice = document.getElementById('payment-locked-notice');
  lockedNotice.hidden = !locked;
  if (locked) {
    lockedNotice.textContent = order.product_type === 'maintenance'
      ? 'Veuillez signer le contrat de maintenance avant de poursuivre votre commande.'
      : 'Veuillez compléter le questionnaire avant de poursuivre votre commande.';
  }
  document.getElementById('payment-methods').hidden = locked;
  if (locked) return;

  if (!interacInfo) {
    try { interacInfo = await Api.getInteracInfo(); } catch (e) { interacInfo = { email: '—' }; }
  }
  document.getElementById('interac-email-value').textContent = interacInfo.email;
  document.getElementById('interac-upload-zone').hidden = true;
  pendingInteracPaymentId = null;

  await loadPaymentHistory(orderId);
}

async function startInteracPayment() {
  const amountType = document.querySelector('input[name="interac-amount"]:checked').value;
  const btn = document.getElementById('interac-start-btn');
  const restore = setButtonLoading(btn, 'Création…');
  try {
    const payment = await Api.createInteracPayment(currentPaymentOrderId, amountType);
    pendingInteracPaymentId = payment.id;
    document.getElementById('interac-upload-zone').hidden = false;
    await loadPaymentHistory(currentPaymentOrderId);
  } catch (err) {
    alert(err.message);
  } finally {
    restore();
  }
}

async function uploadInteracProof() {
  const input = document.getElementById('interac-proof-input');
  if (!pendingInteracPaymentId) { alert('Veuillez d\'abord cliquer sur "J\'ai effectué mon paiement".'); return; }
  if (!input.files || input.files.length === 0) { alert('Veuillez sélectionner un fichier.'); return; }

  const btn = document.getElementById('interac-upload-btn');
  const restore = setButtonLoading(btn, 'Envoi…');
  try {
    await Api.uploadPaymentProof(pendingInteracPaymentId, input.files[0]);
    document.getElementById('interac-upload-zone').hidden = true;
    input.value = '';
    pendingInteracPaymentId = null;
    await loadPaymentHistory(currentPaymentOrderId);
    alert('Preuve de paiement envoyée. Notre équipe va la valider sous peu.');
  } catch (err) {
    alert(err.message);
  } finally {
    restore();
  }
}

async function startStripeCheckout() {
  const amountType = document.querySelector('input[name="stripe-amount"]:checked').value;
  const btn = document.getElementById('stripe-checkout-btn');
  const restore = setButtonLoading(btn, 'Redirection…');
  try {
    const result = await Api.createStripeCheckout(currentPaymentOrderId, amountType);
    window.location.href = result.checkout_url;
  } catch (err) {
    alert(err.message);
    restore();
  }
}

const PAYMENT_METHOD_LABELS = { interac: 'Virement Interac', stripe: 'Carte (Stripe)' };
const PAYMENT_AMOUNT_LABELS = { deposit: 'Dépôt (40%)', full: 'Montant total' };
const PAYMENT_REQUEST_STATUS_LABELS = {
  pending_proof: 'En attente de votre preuve', pending_validation: 'En attente de validation',
  approved: 'Paiement confirmé', rejected: 'Refusé', stripe_initiated: 'Session Stripe créée',
};

async function loadPaymentHistory(orderId) {
  const container = document.getElementById('payments-history');
  try {
    const list = await Api.getOrderPayments(orderId);
    if (list.length === 0) {
      container.innerHTML = `<p class="dashboard-empty">Aucun paiement enregistré pour cette commande.</p>`;
      return;
    }
    container.innerHTML = list.map(p => `
      <div class="payment-history-card">
        <div>
          <div class="payment-history-method">${PAYMENT_METHOD_LABELS[p.method] || p.method} — ${PAYMENT_AMOUNT_LABELS[p.amount_type] || p.amount_type}</div>
          <div style="font-size:.78rem; color:var(--text-soft);">${new Date(p.created_at).toLocaleDateString('fr-CA')}</div>
          ${p.admin_review_note ? `<div style="font-size:.78rem; color:var(--text-soft); margin-top:4px;">Note : ${escapeHtml(p.admin_review_note)}</div>` : ''}
        </div>
        <div class="payment-history-amount">${p.amount.toLocaleString('fr-CA')} $ CAD</div>
        <span class="status-badge payment-status-${p.status}">${PAYMENT_REQUEST_STATUS_LABELS[p.status] || p.status}</span>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<p class="dashboard-empty">Impossible de charger l'historique des paiements.</p>`;
  }
}

/* ---------- Documents reçus ---------- */
async function loadDocuments() {
  const list = document.getElementById('documents-list');
  try {
    const docs = await Api.getMyDocuments();
    if (docs.length === 0) {
      list.innerHTML = `<p class="dashboard-empty">Aucun document pour le moment.</p>`;
      return;
    }
    list.innerHTML = docs.map(d => `
      <div class="document-card">
        <span>${escapeHtml(d.filename)}</span>
        <a class="btn btn-outline" href="${d.url}" target="_blank" rel="noopener">Télécharger</a>
      </div>
    `).join('');
  } catch (err) {
    list.innerHTML = `<p class="dashboard-empty">Impossible de charger vos documents.</p>`;
  }
}

/* ---------- Utils ---------- */
function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
}

document.addEventListener('DOMContentLoaded', initDashboard);
