// ===========================================================
// CYBER TECK Q — Moteur unifié de l'onglet "Contenu du site"
// v9.7 — TOUT (FAQ, Forfaits, Coordonnées, Pages) est organisé
// dans UNE SEULE barre d'onglets de premier niveau, rien n'est
// laissé empilé verticalement dans la page.
// ===========================================================

let currentCmsTabKey = null;
let currentPageEditorKey = null;
let pageEditorGroupItemsCache = {}; // group_key -> liste d'items (avec id) déjà chargés
let pageEditorOpenGroups = {}; // group_key -> bool (état accordéon ouvert/fermé)

/* ---------- Icônes (tracés partagés avec le site public + icônes admin) ---------- */
const PAGE_EDITOR_TAB_ICONS = {
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 11.5L12 4l9 7.5"/><path d="M5.5 10v9.5a1 1 0 0 0 1 1H9.5a1 1 0 0 0 1-1V15h3v4.5a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1V10"/></svg>',
  rocket: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2c2.5 2.5 4 6 4 10l-4 4-4-4c0-4 1.5-7.5 4-10z"/><path d="M9 16l-3 5 5-3M15 16l3 5-5-3"/><circle cx="12" cy="9" r="1.4" fill="currentColor"/></svg>',
  tag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 12.5l-7.5 7.5a1.5 1.5 0 0 1-2.1 0L3 12.6V5a1 1 0 0 1 1-1h7.6a1.5 1.5 0 0 1 1.06.44l7.34 7.35a1.5 1.5 0 0 1 0 2.1z"/><circle cx="7.5" cy="7.5" r="1.3" fill="currentColor"/></svg>',
  compass: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><circle cx="12" cy="12" r="4.2"/></svg>',
  quote: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M9.5 7.5C7 7.5 5 9.5 5 12v5h5v-5H7.2c.1-1.4 1.1-2.5 2.3-2.5V7.5zm9 0c-2.5 0-4.5 2-4.5 4.5v5h5v-5h-2.8c.1-1.4 1.1-2.5 2.3-2.5V7.5z"/></svg>',
  support: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 13a9 9 0 0118 0"/><rect x="3" y="13" width="4" height="6" rx="1.2"/><rect x="17" y="13" width="4" height="6" rx="1.2"/></svg>',
  gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 13a7.4 7.4 0 0 0 0-2l2-1.6-2-3.4-2.4.8a7.5 7.5 0 0 0-1.7-1l-.3-2.5h-4l-.3 2.5a7.5 7.5 0 0 0-1.7 1l-2.4-.8-2 3.4 2 1.6a7.4 7.4 0 0 0 0 2l-2 1.6 2 3.4 2.4-.8a7.5 7.5 0 0 0 1.7 1l.3 2.5h4l.3-2.5a7.5 7.5 0 0 0 1.7-1l2.4.8 2-3.4-2-1.6z"/></svg>',
  star: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2.5l2.9 6 6.6.9-4.8 4.6 1.1 6.6L12 17.6l-5.8 3 1.1-6.6L2.5 9.4l6.6-.9L12 2.5z"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2.5l7.5 3.2v6c0 5-3.3 8.3-7.5 9.8-4.2-1.5-7.5-4.8-7.5-9.8v-6L12 2.5z"/><path d="M8.7 12.2l2.3 2.3 4.3-4.7"/></svg>',
  people: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="9" cy="7" r="3.2"/><path d="M3 20c0-3.3 2.7-5.6 6-5.6s6 2.3 6 5.6"/><circle cx="17" cy="8" r="2.4"/><path d="M14.2 14.8c2.3.2 4.8 1.9 4.8 5.2"/></svg>',
};
function pageEditorTabIcon(key) { return PAGE_EDITOR_TAB_ICONS[key] || PAGE_EDITOR_TAB_ICONS.star; }

/* ---------- Notifications toast (remplace alert()) ---------- */
function ensureToastStack() {
  let stack = document.getElementById('admin-toast-stack');
  if (!stack) {
    stack = document.createElement('div');
    stack.id = 'admin-toast-stack';
    stack.className = 'admin-toast-stack';
    document.body.appendChild(stack);
  }
  return stack;
}
function showAdminToast(message, type) {
  const stack = ensureToastStack();
  const toast = document.createElement('div');
  toast.className = `admin-toast ${type === 'error' ? 'error' : 'success'}`;
  const icon = type === 'error'
    ? '<svg class="admin-toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/></svg>'
    : '<svg class="admin-toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.5 2.5L16 9.5"/></svg>';
  toast.innerHTML = `${icon}<span>${escapeHtml(message)}</span>`;
  stack.appendChild(toast);
  setTimeout(() => {
    toast.style.transition = 'opacity .25s ease';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 250);
  }, 3200);
}

/* ===========================================================
   BARRE D'ONGLETS UNIFIÉE — "Contenu du site"
   Onglets fixes (FAQ, Forfaits, Contact) + un onglet par page
   définie dans CMS_PAGE_SCHEMAS. Un seul panneau visible à la fois.
   =========================================================== */

const CMS_FIXED_TABS = [
  { key: 'faq', label: 'FAQ', icon: 'star', panelId: 'cms-tab-faq' },
  { key: 'pricing', label: 'Forfaits tarifaires', icon: 'shield', panelId: 'cms-tab-pricing' },
  { key: 'contact-info', label: 'Coordonnées de contact', icon: 'people', panelId: 'cms-tab-contact-info' },
];

function setupPageEditor() {
  const tabsContainer = document.getElementById('cms-tabs');
  const pagesContainer = document.getElementById('cms-tab-pages-container');
  if (!tabsContainer || !pagesContainer) return;

  // Génère un panneau caché par page CMS (Accueil, Services, etc.)
  pagesContainer.innerHTML = Object.keys(CMS_PAGE_SCHEMAS).map(key => `
    <div id="cms-tab-page-${key}" class="cms-tab-panel" hidden>
      <div id="page-editor-content-${key}"></div>
    </div>
  `).join('');

  // Construit la liste complète des onglets : fixes d'abord, puis une page à la fois
  const pageTabs = Object.entries(CMS_PAGE_SCHEMAS).map(([key, schema]) => ({
    key: `page-${key}`,
    label: schema.label,
    icon: schema.icon,
    panelId: `cms-tab-page-${key}`,
    pageKey: key,
  }));
  const allTabs = [...CMS_FIXED_TABS, ...pageTabs];

  tabsContainer.innerHTML = allTabs.map((tab, i) => `
    <button type="button" class="page-editor-tab-btn${i === 0 ? ' is-active' : ''}" data-cms-tab="${tab.key}">
      ${pageEditorTabIcon(tab.icon)}
      <span>${escapeHtml(tab.label)}</span>
    </button>
  `).join('');

  tabsContainer.querySelectorAll('[data-cms-tab]').forEach(btn => {
    btn.addEventListener('click', () => selectCmsTab(btn.dataset.cmsTab, allTabs));
  });

  // Ouvre le premier onglet par défaut
  selectCmsTab(allTabs[0].key, allTabs);
}

function selectCmsTab(tabKey, allTabs) {
  currentCmsTabKey = tabKey;
  const tabsContainer = document.getElementById('cms-tabs');
  tabsContainer.querySelectorAll('[data-cms-tab]').forEach(b => {
    b.classList.toggle('is-active', b.dataset.cmsTab === tabKey);
  });

  const tab = allTabs.find(t => t.key === tabKey);
  if (!tab) return;

  document.querySelectorAll('.cms-tab-panel').forEach(panel => { panel.hidden = true; });
  const activePanel = document.getElementById(tab.panelId);
  if (activePanel) activePanel.hidden = false;

  // Si c'est l'onglet d'une page CMS, charge son contenu (titres/textes/listes)
  if (tab.pageKey) {
    pageEditorOpenGroups = {}; // réinitialise l'accordéon en changeant de page
    openPageEditor(tab.pageKey);
  }
}

async function openPageEditor(pageKey) {
  currentPageEditorKey = pageKey;
  const schema = CMS_PAGE_SCHEMAS[pageKey];
  const container = document.getElementById(`page-editor-content-${pageKey}`);
  if (!schema || !container) return;

  container.innerHTML = `<p class="dashboard-loading">Chargement…</p>`;

  try {
    const [blocks, groupsData] = await Promise.all([
      Api.adminListContentBlocks(),
      schema.groups.length > 0
        ? Api.adminListRepeatableItemsForGroups(schema.groups.map(g => g.key))
        : Promise.resolve({}),
    ]);
    const blockValues = Object.fromEntries(blocks.map(b => [b.key, b.value]));
    pageEditorGroupItemsCache = groupsData;

    renderPageEditor(schema, blockValues, groupsData, container);
  } catch (err) {
    container.innerHTML = `<p class="dashboard-empty">Erreur de chargement : ${escapeHtml(err.message)}</p>`;
  }
}

function renderPageEditor(schema, blockValues, groupsData, container) {
  let html = '';

  if (schema.note) {
    html += `<p style="font-size:.84rem; color:var(--admin-text-soft); margin:0 0 18px; padding:10px 14px; background:rgba(11,77,255,.06); border-radius:10px;">${escapeHtml(schema.note)}</p>`;
  }

  // ---- Blocs de texte simples ----
  if (schema.blocks.length > 0) {
    html += `<form class="admin-form-card" id="page-editor-blocks-form" style="margin-bottom:28px;">`;
    html += schema.blocks.map(b => {
      const value = blockValues[b.key] !== undefined ? blockValues[b.key] : '';
      if (b.type === 'textarea') {
        return `<label class="field"><span>${escapeHtml(b.label)}</span><textarea name="${b.key}" rows="3">${escapeHtml(value)}</textarea></label>`;
      }
      return `<label class="field"><span>${escapeHtml(b.label)}</span><input type="text" name="${b.key}" value="${escapeHtml(value)}"></label>`;
    }).join('');
    html += `<button type="submit" class="admin-btn-sm primary">Enregistrer les modifications</button>`;
    html += `</form>`;
  }

  // ---- Groupes d'items répétables (accordéon) ----
  for (const group of schema.groups) {
    const items = groupsData[group.key] || [];
    const isOpen = pageEditorOpenGroups[group.key] === true;
    html += `
      <div class="page-editor-group${isOpen ? ' is-open' : ''}" data-group-key="${group.key}">
        <div class="page-editor-group-header" data-action="toggle-group">
          <h3>${escapeHtml(group.label)}</h3>
          <div style="display:flex; align-items:center; gap:10px;">
            <span class="page-editor-group-count">${items.length} élément${items.length === 1 ? '' : 's'}</span>
            <svg class="page-editor-group-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
          </div>
        </div>
        <div class="page-editor-group-body">
          <div class="page-editor-group-items" id="group-items-${cssEscape(group.key)}">
            ${items.map(item => renderGroupItemCard(group, item)).join('') || '<p class="dashboard-empty">Aucun élément pour le moment.</p>'}
          </div>
          <button type="button" class="admin-btn-sm" data-action="add-group-item" data-group-key="${group.key}">+ Ajouter un élément</button>
        </div>
      </div>
    `;
  }

  container.innerHTML = html;
  wirePageEditorEvents(schema, container);
}

function cssEscape(s) { return s.replace(/[^a-zA-Z0-9_-]/g, '_'); }

function renderGroupItemCard(group, item) {
  const f = item.fields || {};
  const fieldsHtml = group.fields.map(field => {
    const value = f[field.name];
    if (field.type === 'textarea') {
      return `<label class="field"><span>${escapeHtml(field.label)}</span><textarea data-field-name="${field.name}" rows="2">${escapeHtml(value || '')}</textarea></label>`;
    }
    if (field.type === 'checkbox') {
      return `<div class="checkbox-field"><input type="checkbox" data-field-name="${field.name}" id="chk-${item.id}-${field.name}" ${value ? 'checked' : ''}><label for="chk-${item.id}-${field.name}">${escapeHtml(field.label)}</label></div>`;
    }
    if (field.type === 'icon') {
      return `<label class="field"><span>${escapeHtml(field.label)}</span><select data-field-name="${field.name}">${CMS_ICON_OPTIONS.map(opt => `<option value="${opt}" ${value === opt ? 'selected' : ''}>${opt}</option>`).join('')}</select></label>`;
    }
    if (field.type === 'list') {
      const listValue = Array.isArray(value) ? value.join('\n') : '';
      return `<label class="field"><span>${escapeHtml(field.label)}</span><textarea data-field-name="${field.name}" data-field-list="true" rows="4">${escapeHtml(listValue)}</textarea></label>`;
    }
    return `<label class="field"><span>${escapeHtml(field.label)}</span><input type="text" data-field-name="${field.name}" value="${escapeHtml(value || '')}"></label>`;
  }).join('');

  return `
    <div class="page-editor-item-card" data-item-id="${item.id}">
      ${fieldsHtml}
      <div class="checkbox-field"><input type="checkbox" data-field-name="__is_published" ${item.is_published ? 'checked' : ''} id="pub-${item.id}"><label for="pub-${item.id}">Visible sur le site</label></div>
      <div style="display:flex; gap:8px; margin-top:10px; flex-wrap:wrap;">
        <button type="button" class="admin-btn-sm primary" data-action="save-group-item" data-item-id="${item.id}">Enregistrer les modifications</button>
        <button type="button" class="admin-btn-sm" data-action="move-item-up" data-item-id="${item.id}">↑</button>
        <button type="button" class="admin-btn-sm" data-action="move-item-down" data-item-id="${item.id}">↓</button>
        <button type="button" class="admin-btn-sm danger" data-action="delete-group-item" data-item-id="${item.id}">Supprimer</button>
      </div>
    </div>
  `;
}

function wirePageEditorEvents(schema, container) {
  // ---- Accordéon : ouverture/fermeture des groupes ----
  container.querySelectorAll('[data-action="toggle-group"]').forEach(header => {
    header.addEventListener('click', () => {
      const groupEl = header.closest('.page-editor-group');
      const groupKey = groupEl.dataset.groupKey;
      const willOpen = !groupEl.classList.contains('is-open');
      groupEl.classList.toggle('is-open', willOpen);
      pageEditorOpenGroups[groupKey] = willOpen;
    });
  });

  // ---- Sauvegarde des blocs de texte ----
  const blocksForm = container.querySelector('#page-editor-blocks-form');
  if (blocksForm) {
    blocksForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = blocksForm.querySelector('button[type="submit"]');
      const restore = setButtonLoading(submitBtn, 'Enregistrement…');
      try {
        const data = new FormData(blocksForm);
        await Promise.all([...data.entries()].map(([key, value]) => Api.adminUpdateContentBlock(key, value)));
        showAdminToast('Les modifications ont été enregistrées.', 'success');
      } catch (err) {
        showAdminToast(err.message || 'Une erreur est survenue.', 'error');
      } finally {
        restore();
      }
    });
  }

  // ---- Ajout d'un nouvel élément dans un groupe ----
  container.querySelectorAll('[data-action="add-group-item"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const groupKey = btn.dataset.groupKey;
      const group = schema.groups.find(g => g.key === groupKey);
      pageEditorOpenGroups[groupKey] = true; // garde le groupe ouvert après ajout
      try {
        const existing = pageEditorGroupItemsCache[groupKey] || [];
        await Api.adminCreateRepeatableItem(groupKey, group.emptyFields, existing.length);
        await openPageEditor(currentPageEditorKey);
        showAdminToast('Élément ajouté.', 'success');
      } catch (err) {
        showAdminToast(err.message || 'Une erreur est survenue.', 'error');
      }
    });
  });

  // ---- Sauvegarde d'un item existant ----
  container.querySelectorAll('[data-action="save-group-item"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const card = btn.closest('.page-editor-item-card');
      const itemId = btn.dataset.itemId;
      const fields = {};
      let isPublished = true;
      card.querySelectorAll('[data-field-name]').forEach(input => {
        const name = input.dataset.fieldName;
        if (name === '__is_published') { isPublished = input.checked; return; }
        if (input.type === 'checkbox') fields[name] = input.checked;
        else if (input.dataset.fieldList === 'true') fields[name] = input.value.split('\n').map(s => s.trim()).filter(Boolean);
        else fields[name] = input.value;
      });
      const restore = setButtonLoading(btn, 'Enregistrement…');
      try {
        await Api.adminUpdateRepeatableItem(itemId, { fields, is_published: isPublished });
        showAdminToast('Élément enregistré.', 'success');
      } catch (err) {
        showAdminToast(err.message || 'Une erreur est survenue.', 'error');
      } finally {
        restore();
      }
    });
  });

  // ---- Suppression d'un item ----
  container.querySelectorAll('[data-action="delete-group-item"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      if (!confirm('Supprimer cet élément ? Cette action est irréversible.')) return;
      const groupEl = btn.closest('.page-editor-group');
      if (groupEl) pageEditorOpenGroups[groupEl.dataset.groupKey] = true;
      try {
        await Api.adminDeleteRepeatableItem(btn.dataset.itemId);
        await openPageEditor(currentPageEditorKey);
        showAdminToast('Élément supprimé.', 'success');
      } catch (err) {
        showAdminToast(err.message || 'Une erreur est survenue.', 'error');
      }
    });
  });

  // ---- Réordonnancement ----
  container.querySelectorAll('[data-action="move-item-up"], [data-action="move-item-down"]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const groupEl = btn.closest('.page-editor-group');
      const groupKey = groupEl.dataset.groupKey;
      pageEditorOpenGroups[groupKey] = true;
      const itemId = btn.dataset.itemId;
      const items = pageEditorGroupItemsCache[groupKey] || [];
      const ids = items.map(i => i.id);
      const index = ids.indexOf(itemId);
      const direction = btn.dataset.action === 'move-item-up' ? -1 : 1;
      const targetIndex = index + direction;
      if (targetIndex < 0 || targetIndex >= ids.length) return;
      [ids[index], ids[targetIndex]] = [ids[targetIndex], ids[index]];
      try {
        await Api.adminReorderRepeatableItems(groupKey, ids);
        await openPageEditor(currentPageEditorKey);
      } catch (err) {
        showAdminToast(err.message || 'Une erreur est survenue.', 'error');
      }
    });
  });
}
