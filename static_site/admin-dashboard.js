// ===========================================================
// CYBER TECK Q — Panel admin (admin-dashboard.html)
// ===========================================================

const ORDER_STATUS_LABELS = { pending: 'En attente', processing: 'En cours', delivered: 'Livré', cancelled: 'Annulé', archived: 'Archivé' };
const PAYMENT_STATUS_LABELS = { unpaid: 'Non payé', deposit_paid: 'Dépôt reçu', paid: 'Payé', refunded: 'Remboursé' };

let currentAdmin = null;
let allClients = [];
let allOrders = [];

async function initAdminPanel() {
  const guard = document.getElementById('admin-guard');
  const shell = document.getElementById('admin-shell');

  try {
    currentAdmin = await Api.adminGetMyProfile();
  } catch (err) {
    guard.hidden = false;
    shell.hidden = true;
    return;
  }

  guard.hidden = true;
  shell.hidden = false;
  document.getElementById('admin-user-email').textContent = currentAdmin.email;

  setupTabs();
  setupLogout();
  setupGlobalSearch();
  setupClientsPanel();
  setupOrdersPanel();
  setupInvoicesPanel();
  setupMaintenancePanel();
  setupMessagesPanel();
  setupProjectsPanel();
  setupTechnicalFormsPanel();
  setupCmsPanel();
  setupSettingsPanel();
  setupConfirmModal();
  setupPaymentsPanel();
  setupClientDocumentsModal();

  await loadStats();
  await loadUnpaidFollowups();
  await refreshUnreadBadge();
  await refreshPaymentsBadge();
  await refreshMaintenanceBadge();
}

/* ---------- Tabs ---------- */
function setupTabs() {
  const tabs = document.querySelectorAll('.admin-nav-link');
  const panels = document.querySelectorAll('.admin-panel');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('is-active'));
      panels.forEach(p => p.classList.remove('is-active'));
      tab.classList.add('is-active');
      document.querySelector(`.admin-panel[data-panel="${tab.dataset.panel}"]`)?.classList.add('is-active');

      const panel = tab.dataset.panel;
      if (panel === 'reports') loadReports();
      if (panel === 'clients' && allClients.length === 0) loadClients();
      if (panel === 'orders' && allOrders.length === 0) loadOrders();
      if (panel === 'invoices') loadInvoices();
      if (panel === 'maintenance') loadMaintenance();
      if (panel === 'payments') loadPayments();
      if (panel === 'messages') loadMessages();
      if (panel === 'projects') loadProjects();
      if (panel === 'technical-forms') loadTechnicalForms();
      if (panel === 'cms') { loadFaq(); loadPricing(); loadContactInfo(); }
      if (panel === 'audit') loadAuditLogs();
    });
  });
}

/* ---------- Navigation programmatique (utilisée par la recherche globale) ---------- */
function switchToPanel(panelKey) {
  document.querySelector(`.admin-nav-link[data-panel="${panelKey}"]`)?.click();
}

/* ---------- Recherche globale ---------- */
function setupGlobalSearch() {
  const input = document.getElementById('global-search-input');
  const resultsBox = document.getElementById('global-search-results');

  input.addEventListener('input', debounce(async () => {
    const q = input.value.trim();
    if (q.length < 2) { resultsBox.hidden = true; resultsBox.innerHTML = ''; return; }
    try {
      const data = await Api.adminGlobalSearch(q);
      if (data.results.length === 0) {
        resultsBox.innerHTML = `<p class="admin-empty" style="padding:14px;">Aucun résultat pour « ${escapeHtml(q)} ».</p>`;
      } else {
        const typeLabels = { client: 'Client', order: 'Commande', invoice: 'Facture' };
        resultsBox.innerHTML = data.results.map(r => `
          <button type="button" class="admin-global-search-result" data-panel="${r.panel}">
            <span class="admin-global-search-result-type">${typeLabels[r.type] || r.type}</span>
            <span class="admin-global-search-result-title">${escapeHtml(r.title)}</span>
            <span class="admin-global-search-result-subtitle">${escapeHtml(r.subtitle)}</span>
          </button>
        `).join('');
        resultsBox.querySelectorAll('.admin-global-search-result').forEach(btn => {
          btn.addEventListener('click', () => {
            switchToPanel(btn.dataset.panel);
            resultsBox.hidden = true;
            input.value = '';
          });
        });
      }
      resultsBox.hidden = false;
    } catch (err) {
      resultsBox.hidden = true;
    }
  }, 300));

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.admin-global-search')) resultsBox.hidden = true;
  });
}

/* ---------- Relances : commandes impayées ---------- */
async function loadUnpaidFollowups() {
  const tbody = document.getElementById('unpaid-followups-table-body');
  try {
    const followups = await Api.adminListUnpaidFollowups(3);
    if (followups.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="admin-empty">Aucune commande à relancer. 👍</td></tr>`;
      return;
    }
    tbody.innerHTML = followups.map(o => `
      <tr>
        <td>${escapeHtml(o.client_name)}<br><span style="color:var(--admin-text-soft);font-size:.78rem;">${escapeHtml(o.client_email)}</span></td>
        <td>${escapeHtml(o.order_number)}</td>
        <td>${escapeHtml(o.product_name)}</td>
        <td>${o.price.toLocaleString('fr-CA')} $</td>
        <td><strong>${o.days_unpaid} jour(s)</strong></td>
        <td class="admin-actions-cell">
          <a class="admin-btn-sm primary" href="mailto:${escapeHtml(o.client_email)}?subject=${encodeURIComponent('Rappel — ' + o.order_number)}">Relancer par courriel</a>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

function setupLogout() {
  document.getElementById('admin-logout-btn').addEventListener('click', async () => {
    try { await Api.adminLogout(); } catch (e) {}
    window.location.href = 'admin-login.html';
  });
}

/* ---------- Generic confirm modal ---------- */
let confirmCallback = null;
function setupConfirmModal() {
  document.getElementById('confirm-cancel').addEventListener('click', () => {
    document.getElementById('confirm-modal').hidden = true;
  });
  document.getElementById('confirm-ok').addEventListener('click', async () => {
    document.getElementById('confirm-modal').hidden = true;
    if (confirmCallback) await confirmCallback();
  });
}
function askConfirm(title, text, callback) {
  document.getElementById('confirm-modal-title').textContent = title;
  document.getElementById('confirm-modal-text').textContent = text;
  confirmCallback = callback;
  document.getElementById('confirm-modal').hidden = false;
}

/* ---------- Overview / Stats ---------- */
async function loadStats() {
  const grid = document.getElementById('stats-grid');
  try {
    const s = await Api.adminGetStats();
    grid.innerHTML = `
      <div class="admin-stat-card accent"><div class="admin-stat-value">${s.total_clients}</div><div class="admin-stat-label">Clients</div></div>
      <div class="admin-stat-card"><div class="admin-stat-value">${s.total_orders}</div><div class="admin-stat-label">Commandes au total</div></div>
      <div class="admin-stat-card"><div class="admin-stat-value">${s.total_invoices}</div><div class="admin-stat-label">Factures émises</div></div>
      <div class="admin-stat-card accent"><div class="admin-stat-value">${s.total_revenue.toLocaleString('fr-CA')} $</div><div class="admin-stat-label">Revenu total (taxes incl.)</div></div>
      <div class="admin-stat-card"><div class="admin-stat-value">${s.pending_orders}</div><div class="admin-stat-label">Commandes en attente</div></div>
      <div class="admin-stat-card"><div class="admin-stat-value">${s.processing_orders}</div><div class="admin-stat-label">En cours de réalisation</div></div>
      <div class="admin-stat-card"><div class="admin-stat-value">${s.active_maintenance_contracts}</div><div class="admin-stat-label">Contrats maintenance actifs</div></div>
      <div class="admin-stat-card"><div class="admin-stat-value">${s.recent_registrations}</div><div class="admin-stat-label">Nouveaux clients (30j)</div></div>
    `;
  } catch (err) {
    grid.innerHTML = `<p class="admin-empty">Impossible de charger les statistiques.</p>`;
  }
}

/* ---------- Statistiques avancées / rapports ---------- */
let reportsLoaded = false;

function renderBarChart(container, labels, values, formatValue = (v) => v) {
  if (values.every(v => v === 0)) {
    container.innerHTML = `<p class="admin-empty">Aucune donnée pour cette période.</p>`;
    return;
  }
  const max = Math.max(...values, 1);
  container.innerHTML = `
    <div class="admin-bar-chart">
      ${labels.map((label, i) => {
        const v = values[i];
        const heightPct = Math.max((v / max) * 100, v > 0 ? 4 : 0);
        return `
          <div class="admin-bar-chart-col" title="${escapeHtml(label)} : ${escapeHtml(String(formatValue(v)))}">
            <span class="admin-bar-chart-value">${v > 0 ? escapeHtml(String(formatValue(v))) : ''}</span>
            <div class="admin-bar-chart-bar" style="height:${heightPct}%"></div>
            <span class="admin-bar-chart-label">${escapeHtml(label)}</span>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

const REPORT_STATUS_COLORS = { pending: '#F59E0B', processing: '#0B4DFF', delivered: '#15803D', cancelled: '#DC2626', archived: '#5B6B8C' };
const REPORT_PRODUCT_COLORS = { website: '#0B4DFF', mobile_app: '#6B4CFF', maintenance: '#00D9FF' };
const REPORT_PRODUCT_LABELS = { website: 'Site Web', mobile_app: 'Application Mobile', maintenance: 'Maintenance' };

function renderLegendChart(container, counts, colorMap, labelMap = {}) {
  const entries = Object.entries(counts).filter(([, v]) => v > 0);
  if (entries.length === 0) {
    container.innerHTML = `<p class="admin-empty">Aucune commande pour le moment.</p>`;
    return;
  }
  const total = entries.reduce((sum, [, v]) => sum + v, 0);
  container.innerHTML = `
    <div class="admin-donut-legend">
      ${entries.map(([key, count]) => {
        const pct = total > 0 ? Math.round((count / total) * 100) : 0;
        const label = labelMap[key] || (ORDER_STATUS_LABELS[key] || key);
        const color = colorMap[key] || 'var(--admin-primary)';
        return `
          <div class="admin-donut-legend-item">
            <span class="admin-donut-legend-swatch" style="background:${color}"></span>
            <span>${escapeHtml(label)}</span>
            <span class="admin-donut-legend-count">${count} (${pct}%)</span>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

async function loadReports() {
  if (reportsLoaded) return;
  reportsLoaded = true;

  const revenueEl = document.getElementById('report-revenue-chart');
  const ordersEl = document.getElementById('report-orders-chart');
  const clientsEl = document.getElementById('report-clients-chart');
  const statusEl = document.getElementById('report-status-chart');
  const productEl = document.getElementById('report-product-chart');
  const topClientsBody = document.getElementById('report-top-clients-body');

  try {
    const revenue = await Api.adminReportRevenueByMonth(12);
    renderBarChart(revenueEl, revenue.labels, revenue.values, (v) => `${v.toLocaleString('fr-CA')} $`);
  } catch (err) {
    revenueEl.innerHTML = `<p class="admin-empty">Erreur de chargement.</p>`;
  }

  try {
    const orders = await Api.adminReportOrdersByMonth(12);
    renderBarChart(ordersEl, orders.labels, orders.values);
  } catch (err) {
    ordersEl.innerHTML = `<p class="admin-empty">Erreur de chargement.</p>`;
  }

  try {
    const clients = await Api.adminReportClientsByMonth(12);
    renderBarChart(clientsEl, clients.labels, clients.values);
  } catch (err) {
    clientsEl.innerHTML = `<p class="admin-empty">Erreur de chargement.</p>`;
  }

  try {
    const byStatus = await Api.adminReportOrdersByStatus();
    renderLegendChart(statusEl, byStatus, REPORT_STATUS_COLORS, ORDER_STATUS_LABELS);
  } catch (err) {
    statusEl.innerHTML = `<p class="admin-empty">Erreur de chargement.</p>`;
  }

  try {
    const byProduct = await Api.adminReportOrdersByProductType();
    renderLegendChart(productEl, byProduct, REPORT_PRODUCT_COLORS, REPORT_PRODUCT_LABELS);
  } catch (err) {
    productEl.innerHTML = `<p class="admin-empty">Erreur de chargement.</p>`;
  }

  try {
    const topClients = await Api.adminReportTopClients(10);
    if (topClients.length === 0) {
      topClientsBody.innerHTML = `<tr><td colspan="4" class="admin-empty">Aucune facture émise pour le moment.</td></tr>`;
    } else {
      topClientsBody.innerHTML = topClients.map(c => `
        <tr>
          <td>${escapeHtml(c.client_name)}</td>
          <td>${escapeHtml(c.client_email)}</td>
          <td>${c.invoice_count}</td>
          <td>${c.total_revenue.toLocaleString('fr-CA')} $</td>
        </tr>
      `).join('');
    }
  } catch (err) {
    topClientsBody.innerHTML = `<tr><td colspan="4" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}
function setupClientsPanel() {
  document.getElementById('clients-search').addEventListener('input', debounce(loadClients, 350));
  document.getElementById('clients-status-filter').addEventListener('change', loadClients);
  document.getElementById('client-profile-modal-close').addEventListener('click', () => {
    document.getElementById('client-profile-modal').hidden = true;
  });
}

async function loadClients() {
  const tbody = document.getElementById('clients-table-body');
  const search = document.getElementById('clients-search').value.trim();
  const statusFilter = document.getElementById('clients-status-filter').value;

  const params = new URLSearchParams();
  if (search) params.set('search', search);
  if (statusFilter) params.set('is_active', statusFilter);

  try {
    allClients = await Api.adminListClients(`?${params.toString()}`);
    if (allClients.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="admin-empty">Aucun client trouvé.</td></tr>`;
      return;
    }
    tbody.innerHTML = allClients.map(c => `
      <tr>
        <td><a href="#" class="admin-link" data-action="view-profile" data-id="${c.id}">${escapeHtml(c.first_name)} ${escapeHtml(c.last_name)}</a></td>
        <td>${escapeHtml(c.email)}</td>
        <td>${escapeHtml(c.phone || '—')}</td>
        <td>${c.order_count}</td>
        <td><span class="admin-badge ${c.is_active ? 'status-delivered' : 'status-cancelled'}">${c.is_active ? 'Actif' : 'Désactivé'}</span></td>
        <td>${new Date(c.created_at).toLocaleDateString('fr-CA')}</td>
        <td class="admin-actions-cell">
          <button class="admin-btn-sm primary" data-action="view-profile" data-id="${c.id}">Fiche</button>
          ${c.is_active
            ? `<button class="admin-btn-sm" data-action="disable" data-id="${c.id}">Désactiver</button>`
            : `<button class="admin-btn-sm" data-action="enable" data-id="${c.id}">Réactiver</button>`}
          <button class="admin-btn-sm" data-action="reset-password" data-id="${c.id}">Reset mdp</button>
          <button class="admin-btn-sm" data-action="documents" data-id="${c.id}" data-name="${escapeHtml(c.first_name)} ${escapeHtml(c.last_name)}">Documents</button>
          <button class="admin-btn-sm danger" data-action="delete" data-id="${c.id}" data-name="${escapeHtml(c.first_name)} ${escapeHtml(c.last_name)}">Supprimer</button>
        </td>
      </tr>
    `).join('');

    tbody.querySelectorAll('button[data-action], a[data-action]').forEach(btn => {
      btn.addEventListener('click', (e) => { e.preventDefault(); handleClientAction(btn); });
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

async function handleClientAction(btn) {
  const id = btn.dataset.id;
  const action = btn.dataset.action;

  if (action === 'view-profile') {
    openClientProfileModal(id);
  } else if (action === 'disable') {
    await Api.adminDisableClient(id); loadClients();
  } else if (action === 'enable') {
    await Api.adminEnableClient(id); loadClients();
  } else if (action === 'reset-password') {
    try {
      const res = await Api.adminSendPasswordReset(id);
      alert(res.message);
    } catch (err) { alert(err.message); }
  } else if (action === 'documents') {
    openClientDocumentsModal(id, btn.dataset.name);
  } else if (action === 'delete') {
    askConfirm(
      'Supprimer ce client ?',
      `Toutes les données de ${btn.dataset.name} (commandes, factures, formulaires) seront définitivement supprimées. Cette action est irréversible.`,
      async () => { await Api.adminDeleteClient(id); loadClients(); loadStats(); }
    );
  }
}

/* ---------- Fiche client détaillée ---------- */
async function openClientProfileModal(clientId) {
  const modal = document.getElementById('client-profile-modal');
  const content = document.getElementById('client-profile-modal-content');
  document.getElementById('client-profile-modal-title').textContent = 'Fiche client';
  content.innerHTML = `<p class="admin-empty">Chargement…</p>`;
  modal.hidden = false;

  try {
    const data = await Api.adminGetClientProfile(clientId);
    const c = data.client;
    document.getElementById('client-profile-modal-title').textContent = `${c.first_name} ${c.last_name}`;

    const ordersRows = data.orders.length > 0
      ? data.orders.map(o => `
          <tr>
            <td>${escapeHtml(o.order_number)}</td>
            <td>${escapeHtml(o.product_name)}</td>
            <td>${o.price.toLocaleString('fr-CA')} $</td>
            <td><span class="admin-badge status-${o.status}">${ORDER_STATUS_LABELS[o.status] || o.status}</span></td>
            <td><span class="admin-badge payment-${o.payment_status}">${PAYMENT_STATUS_LABELS[o.payment_status] || o.payment_status}</span></td>
            <td>${o.project_progress}%</td>
          </tr>
        `).join('')
      : `<tr><td colspan="6" class="admin-empty">Aucune commande.</td></tr>`;

    const invoicesRows = data.invoices.length > 0
      ? data.invoices.map(inv => `
          <tr>
            <td>${escapeHtml(inv.invoice_number)}</td>
            <td>${inv.total.toLocaleString('fr-CA')} $</td>
            <td>${new Date(inv.created_at).toLocaleDateString('fr-CA')}</td>
          </tr>
        `).join('')
      : `<tr><td colspan="3" class="admin-empty">Aucune facture.</td></tr>`;

    const formsHtml = data.technical_forms.length > 0
      ? data.technical_forms.map(f => `<li>${f.company_name ? escapeHtml(f.company_name) : 'Questionnaire'} — reçu le ${new Date(f.submitted_at).toLocaleDateString('fr-CA')}</li>`).join('')
      : '<li style="color:var(--admin-text-soft);">Aucun questionnaire soumis.</li>';

    const documentsHtml = data.documents.length > 0
      ? data.documents.map(d => `<li>${escapeHtml(d.filename)} — ${new Date(d.created_at).toLocaleDateString('fr-CA')}</li>`).join('')
      : '<li style="color:var(--admin-text-soft);">Aucun document envoyé.</li>';

    content.innerHTML = `
      <div class="admin-stats-grid" style="grid-template-columns:repeat(3, 1fr); margin-bottom:20px;">
        <div class="admin-stat-card"><div class="admin-stat-value">${c.order_count}</div><div class="admin-stat-label">Commandes</div></div>
        <div class="admin-stat-card"><div class="admin-stat-value">${data.invoices.length}</div><div class="admin-stat-label">Factures</div></div>
        <div class="admin-stat-card accent"><div class="admin-stat-value">${data.total_revenue.toLocaleString('fr-CA')} $</div><div class="admin-stat-label">Revenu total</div></div>
      </div>

      <p style="font-size:.86rem; margin:0 0 18px;"><strong>Courriel :</strong> ${escapeHtml(c.email)}${c.phone ? ` &nbsp;•&nbsp; <strong>Téléphone :</strong> ${escapeHtml(c.phone)}` : ''}<br>
      <strong>Client depuis :</strong> ${new Date(c.created_at).toLocaleDateString('fr-CA')} &nbsp;•&nbsp; <strong>Statut :</strong> ${c.is_active ? 'Actif' : 'Désactivé'}</p>

      <h4 style="margin:0 0 8px; font-size:.92rem;">Commandes</h4>
      <div class="admin-table-wrap" style="margin-bottom:18px;">
        <table class="admin-table">
          <thead><tr><th>N°</th><th>Produit</th><th>Prix</th><th>Statut</th><th>Paiement</th><th>Avancement</th></tr></thead>
          <tbody>${ordersRows}</tbody>
        </table>
      </div>

      <h4 style="margin:0 0 8px; font-size:.92rem;">Factures</h4>
      <div class="admin-table-wrap" style="margin-bottom:18px;">
        <table class="admin-table">
          <thead><tr><th>N°</th><th>Total</th><th>Émise le</th></tr></thead>
          <tbody>${invoicesRows}</tbody>
        </table>
      </div>

      <h4 style="margin:0 0 8px; font-size:.92rem;">Formulaires techniques</h4>
      <ul style="margin:0 0 18px; padding-left:18px; font-size:.86rem;">${formsHtml}</ul>

      <h4 style="margin:0 0 8px; font-size:.92rem;">Documents envoyés</h4>
      <ul style="margin:0; padding-left:18px; font-size:.86rem;">${documentsHtml}</ul>
    `;
  } catch (err) {
    content.innerHTML = `<p class="admin-empty">Erreur de chargement de la fiche.</p>`;
  }
}

/* ---------- Orders (CRM) ---------- */
function setupOrdersPanel() {
  document.getElementById('orders-status-filter').addEventListener('change', loadOrders);

  const orderForm = document.getElementById('order-form');
  document.getElementById('cancel-order').addEventListener('click', () => { document.getElementById('order-modal').hidden = true; });

  const slider = document.getElementById('order-progress-slider');
  slider.addEventListener('input', () => updateProgressPreview(parseInt(slider.value, 10)));

  orderForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = new FormData(orderForm);
    const id = data.get('id');
    const payload = {
      status: data.get('status'),
      payment_status: data.get('payment_status'),
      project_progress: parseInt(data.get('project_progress'), 10) || 0,
      expected_delivery_date: data.get('expected_delivery_date') || null,
      notes: data.get('notes') || null,
    };
    try {
      await Api.adminUpdateOrder(id, payload);
      document.getElementById('order-modal').hidden = true;
      await Promise.all([loadOrders(), loadStats()]);
    } catch (err) { alert(err.message); }
  });
}

const STEP_LABELS_BY_THRESHOLD = [[0, 'Projet reçu'], [20, 'Analyse'], [40, 'Développement'], [60, 'Intégration'], [80, 'Vérifications'], [100, 'Projet terminé']];
function stepLabelFor(progress) {
  let label = STEP_LABELS_BY_THRESHOLD[0][1];
  for (const [threshold, name] of STEP_LABELS_BY_THRESHOLD) {
    if (progress >= threshold) label = name; else break;
  }
  return label;
}
function colorFor(progress) {
  if (progress <= 30) return 'red';
  if (progress <= 70) return 'yellow';
  return 'green';
}
function updateProgressPreview(progress) {
  document.getElementById('order-progress-value').textContent = progress;
  document.getElementById('order-progress-step').textContent = stepLabelFor(progress);
  const fill = document.getElementById('order-progress-preview');
  fill.style.width = `${progress}%`;
  fill.style.background = { red: '#DC2626', yellow: '#F59E0B', green: '#16A34A' }[colorFor(progress)];
}

async function loadOrders() {
  const tbody = document.getElementById('orders-table-body');
  const statusFilter = document.getElementById('orders-status-filter').value;
  const params = statusFilter ? `?status=${statusFilter}` : '';

  try {
    allOrders = await Api.adminListOrders(params);
    if (allOrders.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" class="admin-empty">Aucune commande trouvée.</td></tr>`;
      return;
    }
    tbody.innerHTML = allOrders.map(o => `
      <tr>
        <td>${escapeHtml(o.order_number)}</td>
        <td>${escapeHtml(o.client_name)}<br><span style="color:var(--text-soft);font-size:.78rem;">${escapeHtml(o.client_email)}</span></td>
        <td>${escapeHtml(o.product_name)}</td>
        <td>${o.price.toLocaleString('fr-CA')} $</td>
        <td><span class="admin-badge status-${o.status}">${ORDER_STATUS_LABELS[o.status]}</span></td>
        <td><span class="admin-badge payment-${o.payment_status}">${PAYMENT_STATUS_LABELS[o.payment_status]}</span></td>
        <td>${o.project_progress}% — ${escapeHtml(o.progress_step_label)}${o.expected_delivery_date ? `<br><span style="color:var(--text-soft);font-size:.76rem;">Livraison : ${new Date(o.expected_delivery_date).toLocaleDateString('fr-CA')}</span>` : ''}</td>
        <td>${o.has_invoice ? escapeHtml(o.invoice_number) : '—'}</td>
        <td class="admin-actions-cell">
          <button class="admin-btn-sm primary" data-action="edit-order" data-id="${o.id}">Modifier</button>
        </td>
      </tr>
    `).join('');

    tbody.querySelectorAll('[data-action="edit-order"]').forEach(btn => {
      btn.addEventListener('click', () => openOrderModal(btn.dataset.id));
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

function openOrderModal(orderId) {
  const order = allOrders.find(o => o.id === orderId);
  if (!order) return;
  const form = document.getElementById('order-form');
  form.querySelector('[name="id"]').value = order.id;
  form.querySelector('[name="status"]').value = order.status;
  form.querySelector('[name="payment_status"]').value = order.payment_status;
  form.querySelector('[name="project_progress"]').value = order.project_progress;
  form.querySelector('[name="expected_delivery_date"]').value = order.expected_delivery_date || '';
  form.querySelector('[name="notes"]').value = order.notes || '';
  updateProgressPreview(order.project_progress);
  document.getElementById('order-modal').hidden = false;
}

/* ---------- Factures ---------- */
let allInvoices = [];

function setupInvoicesPanel() {
  document.getElementById('invoices-search').addEventListener('input', debounce(loadInvoices, 350));
}

async function loadInvoices() {
  const tbody = document.getElementById('invoices-table-body');
  const search = document.getElementById('invoices-search').value.trim();
  const params = search ? `?search=${encodeURIComponent(search)}` : '';

  try {
    allInvoices = await Api.adminListInvoices(params);
    if (allInvoices.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" class="admin-empty">Aucune facture trouvée.</td></tr>`;
      return;
    }
    tbody.innerHTML = allInvoices.map(inv => `
      <tr>
        <td>${escapeHtml(inv.invoice_number)}</td>
        <td>${escapeHtml(inv.client_name)}<br><span style="color:var(--admin-text-soft);font-size:.78rem;">${escapeHtml(inv.client_email)}</span></td>
        <td>${inv.order_number ? escapeHtml(inv.order_number) : '—'}${inv.product_name ? `<br><span style="color:var(--admin-text-soft);font-size:.78rem;">${escapeHtml(inv.product_name)}</span>` : ''}</td>
        <td>${inv.subtotal.toLocaleString('fr-CA')} $</td>
        <td>${inv.gst_amount.toLocaleString('fr-CA')} $</td>
        <td>${inv.qst_amount.toLocaleString('fr-CA')} $</td>
        <td><strong>${inv.total.toLocaleString('fr-CA')} $</strong></td>
        <td>${new Date(inv.created_at).toLocaleDateString('fr-CA')}</td>
        <td class="admin-actions-cell">
          ${inv.has_pdf ? `<button class="admin-btn-sm primary" data-action="download-invoice" data-id="${inv.id}">PDF</button>` : '<span style="color:var(--admin-text-soft);font-size:.78rem;">PDF indisponible</span>'}
          <button class="admin-btn-sm" data-action="resend-invoice" data-id="${inv.id}">Renvoyer</button>
        </td>
      </tr>
    `).join('');

    tbody.querySelectorAll('[data-action="download-invoice"]').forEach(btn => {
      btn.addEventListener('click', () => Api.adminDownloadInvoice(btn.dataset.id));
    });
    tbody.querySelectorAll('[data-action="resend-invoice"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const restore = setButtonLoading(btn, '…');
        try {
          const res = await Api.adminResendInvoice(btn.dataset.id);
          showAdminToast(res.message, 'success');
        } catch (err) {
          showAdminToast(err.message || 'Une erreur est survenue.', 'error');
        } finally {
          restore();
        }
      });
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

/* ---------- Maintenance ---------- */
let allMaintenanceContracts = [];
let currentMaintenanceContractId = null;

const RENEWAL_STATE_LABELS = {
  active: 'Actif', renewal_soon: 'À renouveler bientôt', expired: 'Expiré',
  unpaid: 'Non payé', cancelled: 'Annulé',
};

function setupMaintenancePanel() {
  document.getElementById('maintenance-state-filter').addEventListener('change', loadMaintenance);

  document.getElementById('cancel-maintenance-notes').addEventListener('click', () => {
    document.getElementById('maintenance-notes-modal').hidden = true;
  });
  document.getElementById('maintenance-notes-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const form = e.target;
    const submitBtn = form.querySelector('button[type="submit"]');
    const restore = setButtonLoading(submitBtn, 'Enregistrement…');
    try {
      const data = new FormData(form);
      await Api.adminUpdateMaintenanceNotes(data.get('id'), data.get('notes'));
      document.getElementById('maintenance-notes-modal').hidden = true;
      showAdminToast('Notes enregistrées.', 'success');
      await loadMaintenance();
    } catch (err) {
      showAdminToast(err.message || 'Une erreur est survenue.', 'error');
    } finally {
      restore();
    }
  });
}

async function refreshMaintenanceBadge() {
  try {
    const summary = await Api.adminGetMaintenanceSummary();
    const badge = document.getElementById('maintenance-renewal-badge');
    const count = (summary.renewal_soon || 0) + (summary.expired || 0);
    if (count > 0) { badge.textContent = count; badge.hidden = false; }
    else { badge.hidden = true; }
  } catch (err) { /* silencieux */ }
}

async function loadMaintenance() {
  const summaryGrid = document.getElementById('maintenance-summary-grid');
  const tbody = document.getElementById('maintenance-table-body');
  const stateFilter = document.getElementById('maintenance-state-filter').value;
  const params = stateFilter ? `?state_filter=${stateFilter}` : '';

  try {
    const summary = await Api.adminGetMaintenanceSummary();
    summaryGrid.innerHTML = `
      <div class="admin-stat-card accent"><div class="admin-stat-value">${summary.active}</div><div class="admin-stat-label">Contrats actifs</div></div>
      <div class="admin-stat-card"><div class="admin-stat-value">${summary.renewal_soon}</div><div class="admin-stat-label">À renouveler bientôt</div></div>
      <div class="admin-stat-card"><div class="admin-stat-value">${summary.expired}</div><div class="admin-stat-label">Expirés</div></div>
      <div class="admin-stat-card"><div class="admin-stat-value">${summary.total}</div><div class="admin-stat-label">Total des contrats</div></div>
    `;
  } catch (err) {
    summaryGrid.innerHTML = `<p class="admin-empty">Impossible de charger le résumé.</p>`;
  }

  try {
    allMaintenanceContracts = await Api.adminListMaintenance(params);
    if (allMaintenanceContracts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="admin-empty">Aucun contrat de maintenance trouvé.</td></tr>`;
      return;
    }
    tbody.innerHTML = allMaintenanceContracts.map(c => {
      const contractCell = !c.contract_id
        ? '<span style="color:var(--admin-text-soft);">Non créé</span>'
        : c.contract_status === 'signed'
          ? `<span class="admin-badge renewal-active">Signé</span><br><span style="color:var(--admin-text-soft);font-size:.76rem;">${new Date(c.contract_signed_at).toLocaleDateString('fr-CA')}</span>`
          : '<span class="admin-badge renewal-unpaid">Brouillon</span>';
      return `
      <tr>
        <td>${escapeHtml(c.client_name)}<br><span style="color:var(--admin-text-soft);font-size:.78rem;">${escapeHtml(c.client_email)}</span></td>
        <td>${escapeHtml(c.order_number)}</td>
        <td>${new Date(c.started_at).toLocaleDateString('fr-CA')}</td>
        <td>${new Date(c.renewal_date).toLocaleDateString('fr-CA')}${c.days_remaining >= 0 ? `<br><span style="color:var(--admin-text-soft);font-size:.76rem;">${c.days_remaining} jour(s) restant(s)</span>` : ''}</td>
        <td><span class="admin-badge renewal-${c.renewal_state}">${RENEWAL_STATE_LABELS[c.renewal_state] || c.renewal_state}</span></td>
        <td>${contractCell}</td>
        <td style="max-width:200px; white-space:normal;">${c.notes ? escapeHtml(c.notes) : '<span style="color:var(--admin-text-soft);">—</span>'}</td>
        <td class="admin-actions-cell">
          <button class="admin-btn-sm" data-action="edit-maintenance-notes" data-id="${c.id}">Notes</button>
          ${c.contract_has_pdf ? `<button class="admin-btn-sm" data-action="download-maintenance-contract" data-contract-id="${c.contract_id}">Contrat PDF</button>` : ''}
        </td>
      </tr>
    `;
    }).join('');

    tbody.querySelectorAll('[data-action="edit-maintenance-notes"]').forEach(btn => {
      btn.addEventListener('click', () => openMaintenanceNotesModal(btn.dataset.id));
    });
    tbody.querySelectorAll('[data-action="download-maintenance-contract"]').forEach(btn => {
      btn.addEventListener('click', () => Api.adminDownloadMaintenanceContract(btn.dataset.contractId));
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="8" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

function openMaintenanceNotesModal(contractId) {
  const contract = allMaintenanceContracts.find(c => c.id === contractId);
  if (!contract) return;
  currentMaintenanceContractId = contractId;
  const form = document.getElementById('maintenance-notes-form');
  form.querySelector('[name="id"]').value = contract.id;
  form.querySelector('[name="notes"]').value = contract.notes || '';
  document.getElementById('maintenance-notes-modal').hidden = false;
}

/* ---------- Projects (portfolio) ---------- */
let allProjects = [];
let currentProjectId = null;

function setupProjectsPanel() {
  document.getElementById('add-project-btn').addEventListener('click', () => openProjectModal(null));
  document.getElementById('cancel-project').addEventListener('click', () => { document.getElementById('project-modal').hidden = true; });

  const form = document.getElementById('project-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const submitBtn = form.querySelector('button[type="submit"]');
    const restore = setButtonLoading(submitBtn, 'Enregistrement…');
    try {
      const data = new FormData(form);
      const id = data.get('id');

      // Upload de l'image principale, si un nouveau fichier a été choisi
      const previewInput = document.getElementById('project-preview-image-input');
      let preview_image_path;
      if (previewInput.files && previewInput.files.length > 0) {
        const uploadRes = await Api.adminUploadCmsImage(previewInput.files[0]);
        preview_image_path = uploadRes.url;
      }

      const payload = {
        title: data.get('title'),
        client_name: data.get('client_name') || null,
        description: data.get('description') || null,
        technologies: data.get('technologies') || null,
        external_link: data.get('external_link') || null,
        is_published: form.querySelector('[name="is_published"]').checked,
      };
      if (preview_image_path) payload.preview_image_path = preview_image_path;

      if (id) {
        await Api.adminUpdateProject(id, payload);
      } else {
        const created = await Api.adminCreateProject(payload);
        currentProjectId = created.id;
      }
      document.getElementById('project-modal').hidden = true;
      previewInput.value = '';
      loadProjects();
    } catch (err) {
      alert(err.message);
    } finally {
      restore();
    }
  });

  document.getElementById('project-gallery-add-btn').addEventListener('click', async () => {
    const input = document.getElementById('project-gallery-input');
    if (!currentProjectId) { alert('Enregistrez d\'abord le projet avant d\'ajouter des médias à sa galerie.'); return; }
    if (!input.files || input.files.length === 0) { alert('Veuillez sélectionner un fichier.'); return; }
    try {
      await Api.adminAddProjectGalleryMedia(currentProjectId, input.files[0]);
      input.value = '';
      await refreshGalleryPreview(currentProjectId);
      loadProjects();
    } catch (err) { alert(err.message); }
  });
}

async function refreshGalleryPreview(projectId) {
  const grid = document.getElementById('project-gallery-grid');
  try {
    allProjects = await Api.adminListProjects();
    const p = allProjects.find(x => x.id === projectId);
    if (!p || !p.gallery_images || p.gallery_images.length === 0) {
      grid.innerHTML = `<p style="color:var(--text-soft); font-size:.82rem;">Aucun média dans la galerie.</p>`;
      return;
    }
    grid.innerHTML = p.gallery_images.map(url => {
      const fileId = url.split('/').pop();
      const isVideo = /\.(mp4|webm|mov)$/i.test(url) || true; // type réel inconnu côté client sans content-type ; on affiche un lien générique
      return `
        <div style="position:relative; width:90px; height:90px; border-radius:8px; overflow:hidden; border:1px solid var(--border); background:#0001;">
          <a href="${url}" target="_blank" rel="noopener" style="display:flex; align-items:center; justify-content:center; width:100%; height:100%; font-size:.7rem; color:var(--text-soft); text-decoration:none;">Voir le fichier</a>
          <button type="button" data-action="remove-gallery-media" data-file-id="${fileId}" title="Retirer"
            style="position:absolute; top:2px; right:2px; background:#DC2626; color:#fff; border:none; border-radius:50%; width:20px; height:20px; font-size:.7rem; cursor:pointer;">×</button>
        </div>
      `;
    }).join('');
    grid.querySelectorAll('[data-action="remove-gallery-media"]').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          await Api.adminRemoveProjectGalleryMedia(projectId, btn.dataset.fileId);
          await refreshGalleryPreview(projectId);
          loadProjects();
        } catch (err) { alert(err.message); }
      });
    });
  } catch (err) {
    grid.innerHTML = `<p style="color:var(--text-soft); font-size:.82rem;">Erreur de chargement de la galerie.</p>`;
  }
}

async function loadProjects() {
  const tbody = document.getElementById('projects-table-body');
  try {
    allProjects = await Api.adminListProjects();
    if (allProjects.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="admin-empty">Aucun projet. Ajoutez votre première réalisation.</td></tr>`;
      return;
    }
    tbody.innerHTML = allProjects.map(p => `
      <tr>
        <td>${escapeHtml(p.title)}</td>
        <td>${escapeHtml(p.client_name || '—')}</td>
        <td>${p.external_link ? `<a href="${escapeHtml(p.external_link)}" target="_blank" rel="noopener">Lien ↗</a>` : '—'}</td>
        <td><span class="admin-badge ${p.is_published ? 'status-delivered' : 'status-pending'}">${p.is_published ? 'Publié' : 'Brouillon'}</span></td>
        <td class="admin-actions-cell">
          <button class="admin-btn-sm" data-action="edit-project" data-id="${p.id}">Modifier</button>
          <button class="admin-btn-sm danger" data-action="delete-project" data-id="${p.id}" data-title="${escapeHtml(p.title)}">Supprimer</button>
        </td>
      </tr>
    `).join('');

    tbody.querySelectorAll('[data-action="edit-project"]').forEach(btn => btn.addEventListener('click', () => openProjectModal(btn.dataset.id)));
    tbody.querySelectorAll('[data-action="delete-project"]').forEach(btn => {
      btn.addEventListener('click', () => {
        askConfirm('Supprimer ce projet ?', `"${btn.dataset.title}" sera retiré du portfolio public.`, async () => {
          await Api.adminDeleteProject(btn.dataset.id); loadProjects();
        });
      });
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

function openProjectModal(projectId) {
  const form = document.getElementById('project-form');
  form.reset();
  document.getElementById('project-preview-image-input').value = '';
  const gallerySection = document.getElementById('project-gallery-section');
  currentProjectId = projectId;

  if (projectId) {
    const p = allProjects.find(x => x.id === projectId);
    document.getElementById('project-modal-title').textContent = 'Modifier le projet';
    form.querySelector('[name="id"]').value = p.id;
    form.querySelector('[name="title"]').value = p.title;
    form.querySelector('[name="client_name"]').value = p.client_name || '';
    form.querySelector('[name="description"]').value = p.description || '';
    form.querySelector('[name="technologies"]').value = p.technologies || '';
    form.querySelector('[name="external_link"]').value = p.external_link || '';
    form.querySelector('[name="is_published"]').checked = p.is_published;
    document.getElementById('project-preview-current').textContent = p.preview_image_path ? 'Une image principale est déjà définie.' : 'Aucune image définie.';
    gallerySection.hidden = false;
    refreshGalleryPreview(projectId);
  } else {
    document.getElementById('project-modal-title').textContent = 'Ajouter un projet';
    document.getElementById('project-preview-current').textContent = '';
    gallerySection.hidden = true; // la galerie nécessite que le projet existe déjà (id requis pour l'upload)
  }
  document.getElementById('project-modal').hidden = false;
}

/* ---------- Formulaires techniques ---------- */
let allTechnicalForms = [];

const TECH_FORM_FEATURE_LABELS = {
  feature_booking: 'Réservation en ligne', feature_payment: 'Paiement en ligne',
  feature_blog: 'Blogue', feature_gallery: 'Galerie', feature_shop: 'Boutique en ligne',
};

function setupTechnicalFormsPanel() {
  document.getElementById('technical-forms-search').addEventListener('input', debounce(loadTechnicalForms, 350));
  document.getElementById('technical-form-modal-close').addEventListener('click', () => {
    document.getElementById('technical-form-modal').hidden = true;
  });
}

async function loadTechnicalForms() {
  const tbody = document.getElementById('technical-forms-table-body');
  const search = document.getElementById('technical-forms-search').value.trim();
  const params = search ? `?search=${encodeURIComponent(search)}` : '';

  try {
    allTechnicalForms = await Api.adminListTechnicalForms(params);
    if (allTechnicalForms.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="admin-empty">Aucun questionnaire reçu.</td></tr>`;
      return;
    }
    tbody.innerHTML = allTechnicalForms.map(f => `
      <tr>
        <td>${f.company_name ? escapeHtml(f.company_name) : '<span style="color:var(--admin-text-soft);">—</span>'}</td>
        <td>${escapeHtml(f.client_name)}<br><span style="color:var(--admin-text-soft);font-size:.78rem;">${escapeHtml(f.client_email)}</span></td>
        <td>${f.order_number ? escapeHtml(f.order_number) : '—'}</td>
        <td>${f.business_sector ? escapeHtml(f.business_sector) : '<span style="color:var(--admin-text-soft);">—</span>'}</td>
        <td>${new Date(f.submitted_at).toLocaleDateString('fr-CA')}</td>
        <td class="admin-actions-cell">
          ${hostingNeedBadge(f)}
          <button class="admin-btn-sm primary" data-action="view-technical-form" data-id="${f.id}">Voir le détail</button>
        </td>
      </tr>
    `).join('');

    tbody.querySelectorAll('[data-action="view-technical-form"]').forEach(btn => {
      btn.addEventListener('click', () => openTechnicalFormModal(btn.dataset.id));
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

/**
 * Petit badge indicateur affiché dans la liste si le client a un besoin
 * d'hébergement/domaine à traiter (nouvel hébergement, aide domaine, ou transfert de site).
 */
function hostingNeedBadge(f) {
  const needsAttention = f.wants_new_hosting || f.wants_domain_help || f.wants_website_transfer;
  if (!needsAttention) return '';
  return `<span class="status-badge" style="background:rgba(37,99,235,.12); color:#1D4ED8; margin-right:6px;" title="Besoin d'hébergement/domaine à traiter">🌐 Hébergement</span>`;
}

function technicalFormRow(label, value) {
  if (!value) return '';
  return `<tr><td style="padding:6px 10px 6px 0; color:var(--admin-text-soft); white-space:nowrap; vertical-align:top;">${escapeHtml(label)}</td><td style="padding:6px 0;">${escapeHtml(value)}</td></tr>`;
}

function technicalFormBoolRow(label, value) {
  const text = value === true ? 'Oui' : value === false ? 'Non' : 'Non précisé';
  return `<tr><td style="padding:6px 10px 6px 0; color:var(--admin-text-soft); white-space:nowrap; vertical-align:top;">${escapeHtml(label)}</td><td style="padding:6px 0;">${text}</td></tr>`;
}

function openTechnicalFormModal(formId) {
  const form = allTechnicalForms.find(f => f.id === formId);
  if (!form) return;

  document.getElementById('technical-form-modal-title').textContent =
    form.company_name ? `Questionnaire — ${form.company_name}` : 'Détail du questionnaire';

  const features = Object.entries(TECH_FORM_FEATURE_LABELS)
    .filter(([key]) => form[key])
    .map(([, label]) => label);

  const rows = [
    technicalFormRow('Client', `${form.client_name} (${form.client_email})`),
    technicalFormRow('Commande', form.order_number),
    technicalFormRow('Entreprise', form.company_name),
    technicalFormRow('Secteur', form.business_sector),
    technicalFormRow('Description', form.description),
    technicalFormRow('Objectifs', form.objectives),
    technicalFormRow('Public cible', form.target_audience),
    technicalFormRow('Pages requises', form.pages_required),
    technicalFormRow('Couleurs souhaitées', form.desired_colors),
    technicalFormRow('Logo existant', form.has_existing_logo ? 'Oui' : 'Non'),
    technicalFormRow('Images fournies', form.has_images ? 'Oui' : 'Non'),
    technicalFormRow('Fonctionnalités désirées', features.length > 0 ? features.join(', ') : 'Aucune'),
    technicalFormRow('Langues', form.languages),
    `<tr><td colspan="2" style="padding:14px 0 6px; font-weight:700; color:var(--admin-text); border-top:1px solid var(--admin-border);">Hébergement Web</td></tr>`,
    technicalFormBoolRow('A un hébergement actuellement', form.has_current_hosting),
    technicalFormRow('Fournisseur d\'hébergement', form.hosting_provider),
    technicalFormRow('Accès à l\'hébergement', form.hosting_access_details),
    technicalFormBoolRow('Souhaite un nouvel hébergement CTQ', form.wants_new_hosting),
    technicalFormBoolRow('Possède déjà un nom de domaine', form.has_domain_name),
    technicalFormRow('Nom de domaine', form.domain_name),
    technicalFormBoolRow('Besoin d\'aide pour acheter un domaine', form.wants_domain_help),
    technicalFormBoolRow('Souhaite transférer un site existant', form.wants_website_transfer),
    technicalFormRow('Sites de référence', form.reference_websites),
    technicalFormRow('Notes additionnelles', form.additional_notes),
    technicalFormRow('Reçu le', new Date(form.submitted_at).toLocaleString('fr-CA')),
  ].filter(Boolean).join('');

  document.getElementById('technical-form-modal-content').innerHTML = `<table style="width:100%; border-collapse:collapse;">${rows}</table>`;
  document.getElementById('technical-form-modal').hidden = false;
}

/* ---------- CMS : FAQ ---------- */
let allFaq = [];

function setupCmsPanel() {
  document.getElementById('add-faq-btn').addEventListener('click', () => openFaqModal(null));
  document.getElementById('cancel-faq').addEventListener('click', () => { document.getElementById('faq-modal').hidden = true; });
  document.getElementById('faq-form').addEventListener('submit', submitFaqForm);

  document.getElementById('add-pricing-btn').addEventListener('click', () => openPricingModal(null));
  document.getElementById('cancel-pricing').addEventListener('click', () => { document.getElementById('pricing-modal').hidden = true; });
  document.getElementById('pricing-form').addEventListener('submit', submitPricingForm);

  document.getElementById('contact-info-form').addEventListener('submit', submitContactInfoForm);

  setupPageEditor();
}

async function loadContactInfo() {
  const form = document.getElementById('contact-info-form');
  try {
    const blocks = await Api.adminListContentBlocks();
    const byKey = Object.fromEntries(blocks.map(b => [b.key, b.value]));
    ['contact.email', 'contact.phone', 'contact.address', 'contact.social_facebook', 'contact.social_instagram', 'contact.social_linkedin']
      .forEach(key => {
        const input = form.querySelector(`[name="${key}"]`);
        if (input) input.value = byKey[key] || '';
      });
  } catch (err) { /* silencieux : les champs restent vides */ }
}

async function submitContactInfoForm(e) {
  e.preventDefault();
  const form = e.target;
  const submitBtn = form.querySelector('button[type="submit"]');
  const restore = setButtonLoading(submitBtn, 'Enregistrement…');
  try {
    const data = new FormData(form);
    const keys = ['contact.email', 'contact.phone', 'contact.address', 'contact.social_facebook', 'contact.social_instagram', 'contact.social_linkedin'];
    await Promise.all(keys.map(key => Api.adminUpdateContentBlock(key, data.get(key) || '')));
    alert('Coordonnées de contact mises à jour.');
  } catch (err) {
    alert(err.message);
  } finally {
    restore();
  }
}

async function loadFaq() {
  const tbody = document.getElementById('faq-table-body');
  try {
    allFaq = await Api.adminListFaq();
    if (allFaq.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="admin-empty">Aucune question.</td></tr>`;
      return;
    }
    tbody.innerHTML = allFaq.map(f => `
      <tr>
        <td>${escapeHtml(f.question)}</td>
        <td><span class="admin-badge ${f.is_published ? 'status-delivered' : 'status-pending'}">${f.is_published ? 'Oui' : 'Non'}</span></td>
        <td>${f.display_order}</td>
        <td class="admin-actions-cell">
          <button class="admin-btn-sm" data-action="edit-faq" data-id="${f.id}">Modifier</button>
          <button class="admin-btn-sm danger" data-action="delete-faq" data-id="${f.id}">Supprimer</button>
        </td>
      </tr>
    `).join('');
    tbody.querySelectorAll('[data-action="edit-faq"]').forEach(btn => btn.addEventListener('click', () => openFaqModal(btn.dataset.id)));
    tbody.querySelectorAll('[data-action="delete-faq"]').forEach(btn => {
      btn.addEventListener('click', () => askConfirm('Supprimer cette question ?', 'Elle disparaîtra de la FAQ publique.', async () => {
        await Api.adminDeleteFaq(btn.dataset.id); loadFaq();
      }));
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

function openFaqModal(id) {
  const form = document.getElementById('faq-form');
  form.reset();
  if (id) {
    const f = allFaq.find(x => x.id === id);
    document.getElementById('faq-modal-title').textContent = 'Modifier la question';
    form.querySelector('[name="id"]').value = f.id;
    form.querySelector('[name="question"]').value = f.question;
    form.querySelector('[name="answer"]').value = f.answer;
    form.querySelector('[name="display_order"]').value = f.display_order;
    form.querySelector('[name="is_published"]').checked = f.is_published;
  } else {
    document.getElementById('faq-modal-title').textContent = 'Ajouter une question';
  }
  document.getElementById('faq-modal').hidden = false;
}

async function submitFaqForm(e) {
  e.preventDefault();
  const form = e.target;
  const data = new FormData(form);
  const id = data.get('id');
  const payload = {
    question: data.get('question'),
    answer: data.get('answer'),
    display_order: parseInt(data.get('display_order'), 10) || 0,
    is_published: form.querySelector('[name="is_published"]').checked,
  };
  try {
    if (id) await Api.adminUpdateFaq(id, payload);
    else await Api.adminCreateFaq(payload);
    document.getElementById('faq-modal').hidden = true;
    loadFaq();
  } catch (err) { alert(err.message); }
}

/* ---------- CMS : Pricing ---------- */
let allPricing = [];

async function loadPricing() {
  const tbody = document.getElementById('pricing-table-body');
  try {
    allPricing = await Api.adminListPricing();
    if (allPricing.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="admin-empty">Aucun forfait.</td></tr>`;
      return;
    }
    tbody.innerHTML = allPricing.map(p => `
      <tr>
        <td>${escapeHtml(p.name)}</td>
        <td>${escapeHtml(p.price)}</td>
        <td>${p.is_featured ? 'Oui' : 'Non'}</td>
        <td><span class="admin-badge ${p.is_published ? 'status-delivered' : 'status-pending'}">${p.is_published ? 'Oui' : 'Non'}</span></td>
        <td class="admin-actions-cell">
          <button class="admin-btn-sm" data-action="edit-pricing" data-id="${p.id}">Modifier</button>
          <button class="admin-btn-sm danger" data-action="delete-pricing" data-id="${p.id}">Supprimer</button>
        </td>
      </tr>
    `).join('');
    tbody.querySelectorAll('[data-action="edit-pricing"]').forEach(btn => btn.addEventListener('click', () => openPricingModal(btn.dataset.id)));
    tbody.querySelectorAll('[data-action="delete-pricing"]').forEach(btn => {
      btn.addEventListener('click', () => askConfirm('Supprimer ce forfait ?', 'Il disparaîtra de la page Tarifs publique.', async () => {
        await Api.adminDeletePricing(btn.dataset.id); loadPricing();
      }));
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

function openPricingModal(id) {
  const form = document.getElementById('pricing-form');
  form.reset();
  if (id) {
    const p = allPricing.find(x => x.id === id);
    document.getElementById('pricing-modal-title').textContent = 'Modifier le forfait';
    form.querySelector('[name="id"]').value = p.id;
    form.querySelector('[name="name"]').value = p.name;
    form.querySelector('[name="price"]').value = p.price;
    form.querySelector('[name="features"]').value = (p.features || []).join('\n');
    form.querySelector('[name="is_featured"]').checked = p.is_featured;
    form.querySelector('[name="is_published"]').checked = p.is_published;
  } else {
    document.getElementById('pricing-modal-title').textContent = 'Ajouter un forfait';
  }
  document.getElementById('pricing-modal').hidden = false;
}

async function submitPricingForm(e) {
  e.preventDefault();
  const form = e.target;
  const data = new FormData(form);
  const id = data.get('id');
  const features = (data.get('features') || '').split('\n').map(s => s.trim()).filter(Boolean);
  const payload = {
    name: data.get('name'),
    price: data.get('price'),
    features,
    is_featured: form.querySelector('[name="is_featured"]').checked,
    is_published: form.querySelector('[name="is_published"]').checked,
  };
  try {
    if (id) await Api.adminUpdatePricing(id, payload);
    else await Api.adminCreatePricing(payload);
    document.getElementById('pricing-modal').hidden = true;
    loadPricing();
  } catch (err) { alert(err.message); }
}

/* ---------- Messages (contact) ---------- */
let allMessages = [];
let currentMessageId = null;

function setupMessagesPanel() {
  document.getElementById('messages-status-filter').addEventListener('change', loadMessages);

  document.getElementById('message-modal-close').addEventListener('click', () => {
    document.getElementById('message-modal').hidden = true;
  });

  document.getElementById('message-toggle-archive').addEventListener('click', async () => {
    const msg = allMessages.find(m => m.id === currentMessageId);
    if (!msg) return;
    await Api.adminUpdateContactMessage(currentMessageId, { is_archived: !msg.is_archived });
    document.getElementById('message-modal').hidden = true;
    loadMessages();
    refreshUnreadBadge();
  });

  document.getElementById('message-delete-btn').addEventListener('click', () => {
    askConfirm('Supprimer ce message ?', 'Cette action est irréversible.', async () => {
      await Api.adminDeleteContactMessage(currentMessageId);
      document.getElementById('message-modal').hidden = true;
      loadMessages();
      refreshUnreadBadge();
    });
  });
}

async function refreshUnreadBadge() {
  try {
    const res = await Api.adminGetUnreadMessageCount();
    const badge = document.getElementById('messages-unread-badge');
    if (res.unread_count > 0) {
      badge.textContent = res.unread_count;
      badge.hidden = false;
    } else {
      badge.hidden = true;
    }
  } catch (err) { /* silencieux */ }
}

async function loadMessages() {
  const tbody = document.getElementById('messages-table-body');
  const filter = document.getElementById('messages-status-filter').value;

  const params = new URLSearchParams();
  if (filter === 'unread') { params.set('is_read', 'false'); params.set('is_archived', 'false'); }
  else if (filter === 'all') { params.set('is_archived', 'false'); }
  else if (filter === 'archived') { params.set('is_archived', 'true'); }

  try {
    allMessages = await Api.adminListContactMessages(`?${params.toString()}`);
    if (allMessages.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="admin-empty">Aucun message.</td></tr>`;
      return;
    }
    tbody.innerHTML = allMessages.map(m => `
      <tr class="${m.is_read ? '' : 'admin-row-unread'}">
        <td>${new Date(m.created_at).toLocaleString('fr-CA')}</td>
        <td>${escapeHtml(m.first_name)} ${escapeHtml(m.last_name)}</td>
        <td>${escapeHtml(m.email)}</td>
        <td>${escapeHtml(m.subject)}</td>
        <td><span class="admin-badge ${m.email_sent ? 'status-delivered' : 'status-cancelled'}">${m.email_sent ? 'Oui' : 'Échec'}</span></td>
        <td><span class="admin-badge ${m.is_read ? 'status-delivered' : 'status-pending'}">${m.is_read ? 'Lu' : 'Non lu'}</span></td>
        <td class="admin-actions-cell">
          <button class="admin-btn-sm" data-action="view-message" data-id="${m.id}">Lire</button>
        </td>
      </tr>
    `).join('');
    tbody.querySelectorAll('[data-action="view-message"]').forEach(btn => {
      btn.addEventListener('click', () => openMessageModal(btn.dataset.id));
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

async function openMessageModal(id) {
  const msg = allMessages.find(m => m.id === id);
  if (!msg) return;
  currentMessageId = id;

  document.getElementById('message-modal-content').innerHTML = `
    <p><strong>${escapeHtml(msg.first_name)} ${escapeHtml(msg.last_name)}</strong> — ${escapeHtml(msg.email)}${msg.phone ? ' — ' + escapeHtml(msg.phone) : ''}</p>
    <p><strong>Sujet :</strong> ${escapeHtml(msg.subject)}</p>
    <p><strong>Reçu le :</strong> ${new Date(msg.created_at).toLocaleString('fr-CA')}</p>
    <p style="margin-top:14px; white-space:pre-wrap; background:rgba(0,0,0,.03); padding:12px; border-radius:8px;">${escapeHtml(msg.message)}</p>
    ${!msg.email_sent ? '<p style="color:#B91C1C; font-weight:600;">⚠ L\'envoi par courriel a échoué — ce message n\'existe qu\'ici.</p>' : ''}
  `;
  document.getElementById('message-toggle-archive').textContent = msg.is_archived ? 'Désarchiver' : 'Archiver';
  document.getElementById('message-modal').hidden = false;

  if (!msg.is_read) {
    await Api.adminUpdateContactMessage(id, { is_read: true });
    msg.is_read = true;
    refreshUnreadBadge();
    loadMessages();
  }
}

/* ---------- Paiements (validation Interac) ---------- */
let allPayments = [];
let currentReviewPaymentId = null;

function setupPaymentsPanel() {
  document.getElementById('payments-filter').addEventListener('change', loadPayments);

  document.getElementById('cancel-payment-review').addEventListener('click', () => {
    document.getElementById('payment-review-modal').hidden = true;
  });

  document.getElementById('payment-review-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    await submitPaymentReview(true);
  });
  document.getElementById('reject-payment-btn').addEventListener('click', async () => {
    await submitPaymentReview(false);
  });
}

async function submitPaymentReview(approve) {
  const form = document.getElementById('payment-review-form');
  const note = form.querySelector('[name="note"]').value || null;
  try {
    await Api.adminReviewPayment(currentReviewPaymentId, approve, note);
    document.getElementById('payment-review-modal').hidden = true;
    await Promise.all([loadPayments(), refreshPaymentsBadge(), loadOrders()]);
  } catch (err) { alert(err.message); }
}

async function refreshPaymentsBadge() {
  try {
    const pending = await Api.adminListPayments('?pending_only=true');
    const badge = document.getElementById('payments-pending-badge');
    if (pending.length > 0) { badge.textContent = pending.length; badge.hidden = false; }
    else { badge.hidden = true; }
  } catch (err) { /* silencieux */ }
}

async function loadPayments() {
  const tbody = document.getElementById('payments-table-body');
  const pendingOnly = document.getElementById('payments-filter').value;
  try {
    allPayments = await Api.adminListPayments(`?pending_only=${pendingOnly}`);
    if (allPayments.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="admin-empty">Aucun paiement trouvé.</td></tr>`;
      return;
    }
    tbody.innerHTML = allPayments.map(p => `
      <tr>
        <td>${escapeHtml(p.client_name || '—')}<br><span style="color:var(--text-soft);font-size:.78rem;">${escapeHtml(p.client_email || '')}</span></td>
        <td>${escapeHtml(p.order_number || '—')}</td>
        <td>${p.amount.toLocaleString('fr-CA')} $</td>
        <td>${p.amount_type === 'deposit' ? 'Dépôt (40%)' : 'Total'}</td>
        <td><span class="admin-badge payment-status-${p.status}">${PAYMENT_REQUEST_LABELS[p.status] || p.status}</span></td>
        <td>${p.proof_file_id ? `<a href="/api/files/${p.proof_file_id}" target="_blank" rel="noopener">Voir</a>` : '—'}</td>
        <td class="admin-actions-cell">
          ${p.status === 'pending_validation'
            ? `<button class="admin-btn-sm primary" data-action="review-payment" data-id="${p.id}">Valider</button>`
            : '—'}
        </td>
      </tr>
    `).join('');
    tbody.querySelectorAll('[data-action="review-payment"]').forEach(btn => {
      btn.addEventListener('click', () => openPaymentReviewModal(btn.dataset.id));
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

const PAYMENT_REQUEST_LABELS = {
  pending_proof: 'En attente de preuve', pending_validation: 'En attente de validation',
  approved: 'Approuvé', rejected: 'Refusé', stripe_initiated: 'Stripe initié',
};

function openPaymentReviewModal(paymentId) {
  const p = allPayments.find(x => x.id === paymentId);
  if (!p) return;
  currentReviewPaymentId = paymentId;
  document.getElementById('payment-review-content').innerHTML = `
    <p><strong>${escapeHtml(p.client_name || '')}</strong> — ${escapeHtml(p.client_email || '')}</p>
    <p>Commande : <strong>${escapeHtml(p.order_number || '')}</strong></p>
    <p>Montant : <strong>${p.amount.toLocaleString('fr-CA')} $ CAD</strong> (${p.amount_type === 'deposit' ? 'dépôt 40%' : 'montant total'})</p>
    ${p.proof_file_id ? `<p><a href="/api/files/${p.proof_file_id}" target="_blank" rel="noopener">Consulter la preuve de paiement ↗</a></p>` : '<p>Aucune preuve jointe.</p>'}
  `;
  document.getElementById('payment-review-form').reset();
  document.getElementById('payment-review-modal').hidden = false;
}

/* ---------- Documents client ---------- */
let currentDocumentsClientId = null;

function setupClientDocumentsModal() {
  document.getElementById('close-client-documents').addEventListener('click', () => {
    document.getElementById('client-documents-modal').hidden = true;
  });
  document.getElementById('send-client-document-btn').addEventListener('click', async () => {
    const input = document.getElementById('client-document-input');
    if (!input.files || input.files.length === 0) { alert('Veuillez sélectionner un fichier.'); return; }
    try {
      await Api.adminSendClientDocument(currentDocumentsClientId, input.files[0]);
      input.value = '';
      await loadClientDocuments(currentDocumentsClientId);
    } catch (err) { alert(err.message); }
  });
}

async function openClientDocumentsModal(clientId, clientName) {
  currentDocumentsClientId = clientId;
  document.getElementById('client-documents-title').textContent = `Documents — ${clientName}`;
  document.getElementById('client-documents-modal').hidden = false;
  await loadClientDocuments(clientId);
}

async function loadClientDocuments(clientId) {
  const tbody = document.getElementById('client-documents-table-body');
  try {
    const docs = await Api.adminListClientDocuments(clientId);
    if (docs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3" class="admin-empty">Aucun document envoyé.</td></tr>`;
      return;
    }
    tbody.innerHTML = docs.map(d => `
      <tr>
        <td>${escapeHtml(d.filename)}</td>
        <td>${new Date(d.created_at).toLocaleDateString('fr-CA')}</td>
        <td><a href="${d.url}" target="_blank" rel="noopener">Voir</a></td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="3" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

/* ---------- Audit log ---------- */
async function loadAuditLogs() {
  const tbody = document.getElementById('audit-table-body');
  try {
    const logs = await Api.adminListAuditLogs('?limit=200');
    if (logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="admin-empty">Aucune entrée.</td></tr>`;
      return;
    }
    tbody.innerHTML = logs.map(l => `
      <tr>
        <td>${new Date(l.created_at).toLocaleString('fr-CA')}</td>
        <td>${escapeHtml(l.actor_type)}</td>
        <td>${escapeHtml(l.action)}</td>
        <td>${escapeHtml(l.target_type || '—')}</td>
        <td>${escapeHtml(l.ip_address || '—')}</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="admin-empty">Erreur de chargement.</td></tr>`;
  }
}

/* ---------- Settings ---------- */
function setupSettingsPanel() {
  const form = document.getElementById('admin-password-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFormMessage(form);
    const data = new FormData(form);
    const payload = { current_password: data.get('current_password'), new_password: data.get('new_password') };
    try {
      await Api.adminChangeMyPassword(payload);
      showFormMessage(form, 'Mot de passe modifié. Redirection…', 'success');
      redirectAfter('admin-login.html', 1200);
    } catch (err) {
      showFormMessage(form, err.message);
    }
  });
}

/* ---------- Utils ---------- */
function escapeHtml(str) {
  if (str == null) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function debounce(fn, delay) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

document.addEventListener('DOMContentLoaded', initAdminPanel);
