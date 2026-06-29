// ===========================================================
// CYBER TECK Q — Contrat de maintenance (contrat-maintenance.html)
// ===========================================================

let mcOrderId = null;
let mcContract = null;
let mcSigMode = 'drawn';
let mcSigCtx = null;
let mcSigDrawing = false;
let mcSigHasStroke = false;

async function initMaintenanceContract() {
  const guard = document.getElementById('mc-guard');
  const content = document.getElementById('mc-content');
  const guardTitle = document.getElementById('mc-guard-title');
  const guardText = document.getElementById('mc-guard-text');

  const params = new URLSearchParams(window.location.search);
  mcOrderId = params.get('order');

  if (!mcOrderId) {
    guard.hidden = false;
    guardTitle.textContent = 'Commande introuvable';
    guardText.textContent = 'Aucune commande n\'a été spécifiée. Retournez à votre tableau de bord pour choisir une commande.';
    return;
  }

  let profile, order;
  try {
    profile = await Api.getMyProfile();
    order = await Api.getOrder(mcOrderId);
  } catch (err) {
    guard.hidden = false;
    guardTitle.textContent = 'Accès refusé';
    guardText.textContent = 'Vous devez être connecté pour accéder à cette commande.';
    return;
  }

  if (order.product_type !== 'maintenance') {
    guard.hidden = false;
    guardTitle.textContent = 'Commande non concernée';
    guardText.textContent = 'Cette commande n\'est pas un contrat de maintenance.';
    return;
  }

  document.getElementById('mc-order-label').textContent = `${order.order_number} — ${order.product_name}`;
  content.hidden = false;

  setupSignaturePad();
  setupSigTabs();
  setupInfoForm(profile);

  document.getElementById('mc-sign-btn').addEventListener('click', handleSign);

  // Charge le contrat existant (DRAFT ou SIGNED) s'il y en a un, sinon pré-remplit depuis le profil
  try {
    mcContract = await Api.getMaintenanceContract(mcOrderId);
    fillFormFromContract(mcContract);
    renderContractDetails(mcContract);
    if (mcContract.status === 'signed') {
      showSignedState(mcContract);
    }
  } catch (err) {
    // Aucun contrat encore créé : pré-remplir avec les infos du profil
    const form = document.getElementById('mc-info-form');
    form.querySelector('[name="client_full_name"]').value = `${profile.first_name} ${profile.last_name}`;
    form.querySelector('[name="client_email"]').value = profile.email;
    if (profile.phone) form.querySelector('[name="client_phone"]').value = profile.phone;
    renderContractDetailsDefaults(order);
  }
}

function renderContractDetailsDefaults(order) {
  document.getElementById('mc-plan').textContent = order.product_name;
  document.getElementById('mc-price').textContent = `${order.price.toLocaleString('fr-CA')} $ CAD / an`;
  document.getElementById('mc-duration').textContent = '12 mois';
  document.getElementById('mc-effective').textContent = '—';
  document.getElementById('mc-expiration').textContent = '—';
}

function renderContractDetails(contract) {
  document.getElementById('mc-contract-number').textContent = contract.contract_number;
  document.getElementById('mc-plan').textContent = contract.maintenance_plan;
  document.getElementById('mc-price').textContent = `${contract.annual_price.toLocaleString('fr-CA')} $ CAD / an`;
  document.getElementById('mc-duration').textContent = `${contract.contract_duration_months} mois`;
  document.getElementById('mc-effective').textContent = new Date(contract.effective_date).toLocaleDateString('fr-CA');
  document.getElementById('mc-expiration').textContent = new Date(contract.expiration_date).toLocaleDateString('fr-CA');
}

function fillFormFromContract(contract) {
  const form = document.getElementById('mc-info-form');
  form.querySelector('[name="client_full_name"]').value = contract.client_full_name || '';
  form.querySelector('[name="company_name"]').value = contract.company_name || '';
  form.querySelector('[name="client_email"]').value = contract.client_email || '';
  form.querySelector('[name="client_phone"]').value = contract.client_phone || '';
  form.querySelector('[name="website_concerned"]').value = contract.website_concerned || '';
  if (contract.signer_name) {
    document.getElementById('mc-signer-name').value = contract.signer_name;
  }
}

function setupInfoForm(profile) {
  const form = document.getElementById('mc-info-form');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const status = document.getElementById('mc-save-status');
    const btn = document.getElementById('mc-save-info-btn');
    const restore = setButtonLoading(btn, 'Enregistrement…');
    status.textContent = '';
    status.className = 'mc-save-status';

    const data = new FormData(form);
    const payload = {};
    for (const [key, value] of data.entries()) payload[key] = value || null;

    try {
      mcContract = await Api.saveMaintenanceContractInfo(mcOrderId, payload);
      renderContractDetails(mcContract);
      status.textContent = 'Informations enregistrées.';
      status.classList.add('is-success');
    } catch (err) {
      status.textContent = err.message;
      status.classList.add('is-error');
    } finally {
      restore();
    }
  });
}

/* ---------- Onglets de signature (dessiner / taper) ---------- */
function setupSigTabs() {
  const tabs = document.querySelectorAll('.mc-sig-tab');
  const padWrap = document.getElementById('mc-sig-pad-wrap');
  const typedWrap = document.getElementById('mc-sig-typed-wrap');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('is-active'));
      tab.classList.add('is-active');
      mcSigMode = tab.dataset.sigMode;
      if (mcSigMode === 'drawn') {
        padWrap.hidden = false;
        typedWrap.hidden = true;
      } else {
        padWrap.hidden = true;
        typedWrap.hidden = false;
      }
    });
  });
}

/* ---------- Pad de signature (canvas, souris + tactile) ---------- */
function setupSignaturePad() {
  const canvas = document.getElementById('mc-signature-canvas');
  const ratio = window.devicePixelRatio || 1;

  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * ratio;
    canvas.height = rect.height * ratio;
    mcSigCtx = canvas.getContext('2d');
    mcSigCtx.scale(ratio, ratio);
    mcSigCtx.lineWidth = 2.2;
    mcSigCtx.lineCap = 'round';
    mcSigCtx.strokeStyle = '#0F172A';
  }
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  function getPos(e) {
    const rect = canvas.getBoundingClientRect();
    const point = e.touches ? e.touches[0] : e;
    return { x: point.clientX - rect.left, y: point.clientY - rect.top };
  }

  function start(e) {
    e.preventDefault();
    mcSigDrawing = true;
    const { x, y } = getPos(e);
    mcSigCtx.beginPath();
    mcSigCtx.moveTo(x, y);
  }
  function move(e) {
    if (!mcSigDrawing) return;
    e.preventDefault();
    const { x, y } = getPos(e);
    mcSigCtx.lineTo(x, y);
    mcSigCtx.stroke();
    mcSigHasStroke = true;
  }
  function end() { mcSigDrawing = false; }

  canvas.addEventListener('mousedown', start);
  canvas.addEventListener('mousemove', move);
  canvas.addEventListener('mouseup', end);
  canvas.addEventListener('mouseleave', end);
  canvas.addEventListener('touchstart', start, { passive: false });
  canvas.addEventListener('touchmove', move, { passive: false });
  canvas.addEventListener('touchend', end);

  document.getElementById('mc-sig-clear').addEventListener('click', () => {
    const rect = canvas.getBoundingClientRect();
    mcSigCtx.clearRect(0, 0, rect.width, rect.height);
    mcSigHasStroke = false;
  });
}

/* ---------- Signature ---------- */
async function handleSign() {
  const signerName = document.getElementById('mc-signer-name').value.trim();
  const accepted = document.getElementById('mc-accept-checkbox').checked;
  const btn = document.getElementById('mc-sign-btn');

  if (!signerName) {
    alert('Veuillez indiquer le nom du signataire.');
    return;
  }
  if (!accepted) {
    alert('Vous devez accepter les termes du contrat avant de signer.');
    return;
  }

  let signatureData = '';
  if (mcSigMode === 'drawn') {
    if (!mcSigHasStroke) {
      alert('Veuillez dessiner votre signature dans la zone prévue, ou utilisez l\'option « Taper mon nom ».');
      return;
    }
    signatureData = document.getElementById('mc-signature-canvas').toDataURL('image/png');
  } else {
    const typed = document.getElementById('mc-sig-typed-input').value.trim();
    if (!typed) {
      alert('Veuillez taper votre nom complet en guise de signature.');
      return;
    }
    signatureData = typed;
  }

  const restore = setButtonLoading(btn, 'Signature en cours…');
  try {
    mcContract = await Api.signMaintenanceContract(mcOrderId, {
      signer_name: signerName,
      client_signature_data: signatureData,
      signature_type: mcSigMode,
      accepted_terms: true,
    });
    showSignedState(mcContract);
  } catch (err) {
    alert(err.message);
    restore();
  }
}

function showSignedState(contract) {
  document.getElementById('mc-info-form').querySelectorAll('input').forEach(i => i.disabled = true);
  document.getElementById('mc-save-info-btn').disabled = true;
  document.getElementById('mc-signature-section').hidden = true;

  const banner = document.getElementById('mc-signed-banner');
  const text = document.getElementById('mc-signed-text');
  const link = document.getElementById('mc-download-link');

  text.textContent = `Le contrat ${contract.contract_number} a été signé le ${new Date(contract.signed_at).toLocaleDateString('fr-CA')}. Une copie PDF vous a été envoyée par courriel.`;
  link.href = `/api/orders/${mcOrderId}/maintenance-contract/download`;
  banner.hidden = false;
}

document.addEventListener('DOMContentLoaded', initMaintenanceContract);
