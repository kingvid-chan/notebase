/**
 * App entry point — initializes routing, checks auth, wires up header.
 */

import { api } from './api.js';
import { state } from './state.js';
import { on, startRouter, navigate } from './router.js';
import { showToast } from './components/toast.js';
import { renderLoginPage } from './pages/login.js';
import { renderRegisterPage } from './pages/register.js';
import { renderNotesPage } from './pages/notes.js';
import { renderNoteNewPage, renderNoteDetailPage } from './pages/note-detail.js';

// ---------------------------------------------------------------------------
// Route registration
// ---------------------------------------------------------------------------

on('login', renderLoginPage);
on('register', renderRegisterPage);
on('notes', renderNotesPage);
on('notes-new', renderNoteNewPage);
on('notes-detail', renderNoteDetailPage);

// ---------------------------------------------------------------------------
// Auth guard: check session on startup
// ---------------------------------------------------------------------------

async function checkAuth() {
    try {
        const data = await api.me();
        state.setCurrentUser(data);
    } catch {
        state.clearUser();
    }
}

// ---------------------------------------------------------------------------
// Header UI update on auth change
// ---------------------------------------------------------------------------

function updateHeader() {
    const userInfo = document.getElementById('user-info');
    const btnLogout = document.getElementById('btn-logout');
    const linkLogin = document.getElementById('link-login');
    const nav = document.getElementById('app-nav');

    if (state.isLoggedIn) {
        if (userInfo) userInfo.textContent = `👤 ${state.currentUser.username}`;
        if (btnLogout) btnLogout.style.display = '';
        if (linkLogin) linkLogin.style.display = 'none';
        if (nav) nav.style.display = '';
    } else {
        if (userInfo) userInfo.textContent = '';
        if (btnLogout) btnLogout.style.display = 'none';
        if (linkLogin) linkLogin.style.display = '';
        if (nav) nav.style.display = 'none';
    }
}

// ---------------------------------------------------------------------------
// Logout handler
// ---------------------------------------------------------------------------

document.getElementById('btn-logout').addEventListener('click', async () => {
    try {
        await api.logout();
    } catch (_) { /* ignore */ }
    state.clearUser();
    showToast('已退出登录');
    navigate('#/login');
});

// ---------------------------------------------------------------------------
// State change → update header
// ---------------------------------------------------------------------------

state.onChange(updateHeader);

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

(async () => {
    await checkAuth();
    updateHeader();
    await startRouter();
})();
