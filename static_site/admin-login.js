// ===========================================================
// CYBER TECK Q — Connexion admin (admin-login.html)
// ===========================================================

document.querySelectorAll('.toggle-password').forEach(btn => {
  btn.addEventListener('click', () => {
    const input = document.getElementById(btn.dataset.target);
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
  });
});

// Si déjà connecté en tant qu'admin, rediriger directement vers le tableau de bord
(async function checkAlreadyLoggedIn() {
  try {
    await Api.adminGetMyProfile();
    window.location.href = 'admin-dashboard.html';
  } catch (err) {
    // pas connecté : rester sur la page de connexion
  }
})();

const form = document.getElementById('admin-login-form');
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearFormMessage(form);
  const submitBtn = form.querySelector('button[type="submit"]');
  const restore = setButtonLoading(submitBtn, 'Connexion…');

  const data = new FormData(form);
  const payload = { email: data.get('email'), password: data.get('password') };

  try {
    await Api.adminLogin(payload);
    showFormMessage(form, 'Connexion réussie. Redirection…', 'success');
    redirectAfter('admin-dashboard.html', 600);
  } catch (err) {
    showFormMessage(form, err.message);
    restore();
  }
});
