// ===========================================================
// CYBER TECK Q — Client API
// Centralise tous les appels vers le backend FastAPI.
// Les cookies de session (HttpOnly) sont envoyés automatiquement
// par le navigateur grâce à credentials: 'include'.
// ===========================================================

const API_BASE = ''; // même origine : le frontend est servi par le même service que l'API

async function apiRequest(path, { method = 'GET', body = null } = {}) {
  const options = {
    method,
    credentials: 'include',
    headers: {},
  };
  if (body !== null) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(API_BASE + path, options);
  } catch (networkError) {
    throw new ApiError('Impossible de joindre le serveur. Vérifiez votre connexion et réessayez.', 0, null);
  }

  let data = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = await response.json().catch(() => null);
  }

  if (!response.ok) {
    const message = extractErrorMessage(data) || `Une erreur est survenue (${response.status}).`;
    throw new ApiError(message, response.status, data);
  }

  return data;
}

// Comme apiRequest, mais pour l'envoi de fichiers (multipart/form-data).
// Ne JAMAIS fixer le header Content-Type ici : le navigateur doit définir
// lui-même la boundary multipart, sinon l'upload échoue silencieusement.
async function apiUpload(path, file, extraFields = {}) {
  const formData = new FormData();
  formData.append('file', file);
  for (const [key, value] of Object.entries(extraFields)) {
    if (value !== null && value !== undefined) formData.append(key, value);
  }

  let response;
  try {
    response = await fetch(API_BASE + path, { method: 'POST', credentials: 'include', body: formData });
  } catch (networkError) {
    throw new ApiError('Impossible de joindre le serveur. Vérifiez votre connexion et réessayez.', 0, null);
  }

  let data = null;
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = await response.json().catch(() => null);
  }

  if (!response.ok) {
    const message = extractErrorMessage(data) || `Une erreur est survenue (${response.status}).`;
    throw new ApiError(message, response.status, data);
  }

  return data;
}

function extractErrorMessage(data) {
  if (!data) return null;
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail)) {
    // Erreurs de validation Pydantic : prendre le premier message lisible
    const first = data.detail[0];
    if (first && first.msg) return first.msg.replace('Value error, ', '');
  }
  return null;
}

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

const Api = {
  // ---------- Auth client ----------
  register: (payload) => apiRequest('/api/auth/register', { method: 'POST', body: payload }),
  login: (payload) => apiRequest('/api/auth/login', { method: 'POST', body: payload }),
  logout: () => apiRequest('/api/auth/logout', { method: 'POST' }),
  forgotPassword: (email) => apiRequest('/api/auth/forgot-password', { method: 'POST', body: { email } }),
  resetPassword: (token, new_password) => apiRequest('/api/auth/reset-password', { method: 'POST', body: { token, new_password } }),

  // ---------- Profil client ----------
  getMyProfile: () => apiRequest('/api/profile/me'),
  updateMyProfile: (payload) => apiRequest('/api/profile/me', { method: 'PUT', body: payload }),
  changeMyPassword: (payload) => apiRequest('/api/profile/change-password', { method: 'POST', body: payload }),
  deleteMyAccount: (payload) => apiRequest('/api/profile/me', { method: 'DELETE', body: payload }),

  // ---------- Marketplace / commandes (panier multi-services, v9.11) ----------
  getMarketplace: () => apiRequest('/api/marketplace'),
  createOrder: (items) => apiRequest('/api/orders', { method: 'POST', body: { items } }), // items: [{product_type, quantity}]
  getMyOrders: () => apiRequest('/api/orders'),
  getOrder: (orderId) => apiRequest(`/api/orders/${orderId}`),
  deleteOrder: (orderId) => apiRequest(`/api/orders/${orderId}`, { method: 'DELETE' }),

  // ---------- Questionnaire technique (un par service du panier, v9.11) ----------
  submitTechnicalForm: (orderItemId, payload) => apiRequest(`/api/order-items/${orderItemId}/technical-form`, { method: 'POST', body: payload }),
  getTechnicalForm: (orderItemId) => apiRequest(`/api/order-items/${orderItemId}/technical-form`),

  // ---------- Contrat de maintenance (un par service Maintenance du panier, v9.11) ----------
  getMaintenanceContract: (orderItemId) => apiRequest(`/api/order-items/${orderItemId}/maintenance-contract`),
  saveMaintenanceContractInfo: (orderItemId, payload) => apiRequest(`/api/order-items/${orderItemId}/maintenance-contract`, { method: 'PUT', body: payload }),
  signMaintenanceContract: (orderItemId, payload) => apiRequest(`/api/order-items/${orderItemId}/maintenance-contract/sign`, { method: 'POST', body: payload }),
  downloadMaintenanceContractPdf: (orderItemId) => { window.open(`/api/order-items/${orderItemId}/maintenance-contract/download`, '_blank'); },

  // ---------- Paiements (client) ----------
  getInteracInfo: () => apiRequest('/api/payments/interac-info'),
  getOrderPayments: (orderId) => apiRequest(`/api/payments/order/${orderId}`),
  createInteracPayment: (orderId, amount_type) => apiRequest('/api/payments/interac', { method: 'POST', body: { order_id: orderId, amount_type } }),
  uploadPaymentProof: (paymentId, file) => apiUpload(`/api/payments/interac/${paymentId}/proof`, file),
  createStripeCheckout: (orderId, amount_type) => apiRequest('/api/payments/stripe/checkout', { method: 'POST', body: { order_id: orderId, amount_type } }),

  // ---------- Documents reçus de l'admin ----------
  getMyDocuments: () => apiRequest('/api/profile/me/documents'),

  // ---------- Factures ----------
  getMyInvoices: () => apiRequest('/api/invoices'),

  // ---------- Contenu public ----------
  getPortfolio: () => apiRequest('/api/portfolio'),
  getPublicFaq: () => apiRequest('/api/cms/faq'),
  getPublicPricing: () => apiRequest('/api/cms/pricing'),

  // ---------- Contact ----------
  sendContactMessage: (payload) => apiRequest('/api/contact', { method: 'POST', body: payload }),

  // ---------- Admin auth ----------
  adminLogin: (payload) => apiRequest('/api/admin/auth/login', { method: 'POST', body: payload }),
  adminLogout: () => apiRequest('/api/admin/auth/logout', { method: 'POST' }),
  adminGetMyProfile: () => apiRequest('/api/admin/profile/me'),
  adminChangeMyPassword: (payload) => apiRequest('/api/admin/profile/change-password', { method: 'POST', body: payload }),

  // ---------- Admin dashboard / CRM ----------
  adminGetStats: () => apiRequest('/api/admin/dashboard/stats'),
  adminListClients: (params = '') => apiRequest(`/api/admin/clients${params}`),
  adminGetClient: (id) => apiRequest(`/api/admin/clients/${id}`),
  adminDisableClient: (id) => apiRequest(`/api/admin/clients/${id}/disable`, { method: 'POST' }),
  adminEnableClient: (id) => apiRequest(`/api/admin/clients/${id}/enable`, { method: 'POST' }),
  adminDeleteClient: (id) => apiRequest(`/api/admin/clients/${id}`, { method: 'DELETE' }),
  adminSendPasswordReset: (id) => apiRequest(`/api/admin/clients/${id}/send-password-reset`, { method: 'POST' }),

  adminListOrders: (params = '') => apiRequest(`/api/admin/orders${params}`),
  adminGetOrder: (id) => apiRequest(`/api/admin/orders/${id}`),
  adminUpdateOrder: (id, payload) => apiRequest(`/api/admin/orders/${id}`, { method: 'PUT', body: payload }),
  adminUpdateOrderItem: (orderId, itemId, payload) => apiRequest(`/api/admin/orders/${orderId}/items/${itemId}`, { method: 'PUT', body: payload }),
  adminGenerateInvoice: (orderId) => apiRequest(`/api/admin/orders/${orderId}/generate-invoice`, { method: 'POST' }),

  adminListProjects: () => apiRequest('/api/admin/projects'),
  adminCreateProject: (payload) => apiRequest('/api/admin/projects', { method: 'POST', body: payload }),
  adminUpdateProject: (id, payload) => apiRequest(`/api/admin/projects/${id}`, { method: 'PUT', body: payload }),
  adminDeleteProject: (id) => apiRequest(`/api/admin/projects/${id}`, { method: 'DELETE' }),

  adminListFaq: () => apiRequest('/api/admin/cms/faq'),
  adminCreateFaq: (payload) => apiRequest('/api/admin/cms/faq', { method: 'POST', body: payload }),
  adminUpdateFaq: (id, payload) => apiRequest(`/api/admin/cms/faq/${id}`, { method: 'PUT', body: payload }),
  adminDeleteFaq: (id) => apiRequest(`/api/admin/cms/faq/${id}`, { method: 'DELETE' }),

  adminListPricing: () => apiRequest('/api/admin/cms/pricing'),
  adminCreatePricing: (payload) => apiRequest('/api/admin/cms/pricing', { method: 'POST', body: payload }),
  adminUpdatePricing: (id, payload) => apiRequest(`/api/admin/cms/pricing/${id}`, { method: 'PUT', body: payload }),
  adminDeletePricing: (id) => apiRequest(`/api/admin/cms/pricing/${id}`, { method: 'DELETE' }),

  adminListContentBlocks: () => apiRequest('/api/admin/cms/content'),
  adminUpdateContentBlock: (key, value) => apiRequest(`/api/admin/cms/content/${key}`, { method: 'PUT', body: { value } }),

  adminListRepeatableItems: (groupKey) => apiRequest(`/api/admin/cms/items/${encodeURIComponent(groupKey)}`),
  adminListRepeatableItemsForGroups: async (groupKeys) => {
    const results = await Promise.all(groupKeys.map(k => apiRequest(`/api/admin/cms/items/${encodeURIComponent(k)}`)));
    return Object.fromEntries(groupKeys.map((k, i) => [k, results[i]]));
  },
  adminCreateRepeatableItem: (groupKey, fields, displayOrder = 0) => apiRequest('/api/admin/cms/items', { method: 'POST', body: { group_key: groupKey, fields, display_order: displayOrder } }),
  adminUpdateRepeatableItem: (itemId, payload) => apiRequest(`/api/admin/cms/items/${itemId}`, { method: 'PUT', body: payload }),
  adminDeleteRepeatableItem: (itemId) => apiRequest(`/api/admin/cms/items/${itemId}`, { method: 'DELETE' }),
  adminReorderRepeatableItems: (groupKey, orderedIds) => apiRequest(`/api/admin/cms/items/${encodeURIComponent(groupKey)}/reorder`, { method: 'POST', body: { ordered_ids: orderedIds } }),

  getPublicContentBlocks: () => apiRequest('/api/cms/content'),
  getPublicRepeatableItemsBulk: (groupKeys) => apiRequest(`/api/cms/items?groups=${encodeURIComponent(groupKeys.join(','))}`),

  adminListAuditLogs: (params = '') => apiRequest(`/api/admin/audit-logs${params}`),

  adminListContactMessages: (params = '') => apiRequest(`/api/admin/contact-messages${params}`),
  adminGetUnreadMessageCount: () => apiRequest('/api/admin/contact-messages/unread-count'),
  adminUpdateContactMessage: (id, payload) => apiRequest(`/api/admin/contact-messages/${id}`, { method: 'PUT', body: payload }),
  adminDeleteContactMessage: (id) => apiRequest(`/api/admin/contact-messages/${id}`, { method: 'DELETE' }),

  // ---------- Admin : paiements (historique complet, v9.11) ----------
  adminListPayments: (params = '') => apiRequest(`/api/admin/payments${params}`),
  adminGetPayment: (id) => apiRequest(`/api/admin/payments/${id}`),
  adminReviewPayment: (id, approve, note) => apiRequest(`/api/admin/payments/${id}/review`, { method: 'POST', body: { approve, note } }),
  adminRefundPayment: (id, amount, reason) => apiRequest(`/api/admin/payments/${id}/refund`, { method: 'POST', body: { amount, reason } }),
  adminExportPaymentsCsv: () => { window.open('/api/admin/payments/export/csv', '_blank'); },

  // ---------- Admin : réglages globaux (v9.11) ----------
  adminGetTaxesSetting: () => apiRequest('/api/admin/settings/taxes'),
  adminUpdateTaxesSetting: (enable_tps_tvq) => apiRequest('/api/admin/settings/taxes', { method: 'PUT', body: { enable_tps_tvq } }),

  // ---------- Admin : médias (CMS sans code) ----------
  adminUploadCmsImage: (file) => apiUpload('/api/admin/media/cms-image', file),
  adminAddProjectGalleryMedia: (projectId, file) => apiUpload(`/api/admin/media/projects/${projectId}/gallery`, file),
  adminRemoveProjectGalleryMedia: (projectId, fileId) => apiRequest(`/api/admin/media/projects/${projectId}/gallery/${fileId}`, { method: 'DELETE' }),
  adminSendClientDocument: (clientId, file, orderId) => apiUpload(`/api/admin/media/clients/${clientId}/documents`, file, { order_id: orderId }),
  adminListClientDocuments: (clientId) => apiRequest(`/api/admin/media/clients/${clientId}/documents`),

  // ---------- Admin : factures ----------
  adminListInvoices: (params = '') => apiRequest(`/api/admin/invoices${params}`),
  adminDownloadInvoice: (id) => { window.open(`/api/admin/invoices/${id}/download`, '_blank'); },
  adminResendInvoice: (id) => apiRequest(`/api/admin/invoices/${id}/resend`, { method: 'POST' }),

  // ---------- Admin : contrats de maintenance ----------
  adminListMaintenance: (params = '') => apiRequest(`/api/admin/maintenance${params}`),
  adminGetMaintenanceSummary: () => apiRequest('/api/admin/maintenance/summary'),
  adminUpdateMaintenanceNotes: (id, notes) => apiRequest(`/api/admin/maintenance/${id}/notes`, { method: 'PUT', body: { notes } }),
  adminDownloadMaintenanceContract: (contractId) => { window.open(`/api/admin/maintenance/contracts/${contractId}/download`, '_blank'); },

  // ---------- Admin : formulaires techniques ----------
  adminListTechnicalForms: (params = '') => apiRequest(`/api/admin/technical-forms${params}`),
  adminGetTechnicalForm: (id) => apiRequest(`/api/admin/technical-forms/${id}`),

  // ---------- Admin : statistiques avancées / rapports ----------
  adminReportRevenueByMonth: (months = 12) => apiRequest(`/api/admin/reports/revenue-by-month?months=${months}`),
  adminReportOrdersByMonth: (months = 12) => apiRequest(`/api/admin/reports/orders-by-month?months=${months}`),
  adminReportClientsByMonth: (months = 12) => apiRequest(`/api/admin/reports/clients-by-month?months=${months}`),
  adminReportOrdersByStatus: () => apiRequest('/api/admin/reports/orders-by-status'),
  adminReportOrdersByProductType: () => apiRequest('/api/admin/reports/orders-by-product-type'),
  adminReportTopClients: (limit = 10) => apiRequest(`/api/admin/reports/top-clients?limit=${limit}`),

  // ---------- Admin : fiche client détaillée ----------
  adminGetClientProfile: (id) => apiRequest(`/api/admin/clients/${id}/profile`),

  // ---------- Admin : recherche globale ----------
  adminGlobalSearch: (q) => apiRequest(`/api/admin/search?q=${encodeURIComponent(q)}`),

  // ---------- Admin : relances commandes impayées ----------
  adminListUnpaidFollowups: (minDays = 3) => apiRequest(`/api/admin/orders/unpaid-followups?min_days=${minDays}`),
};
