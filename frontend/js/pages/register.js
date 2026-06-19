/**
 * Register page.
 */

import { api } from '../api.js';
import { state } from '../state.js';
import { navigate } from '../router.js';
import { showToast } from '../components/toast.js';

export async function renderRegisterPage() {
    if (state.isLoggedIn) {
        navigate('#/notes');
        return;
    }

    const main = document.getElementById('app-main');
    main.innerHTML = `
        <div class="auth-page">
            <div class="auth-card">
                <h2>注册 Notebase</h2>
                <form id="register-form">
                    <div class="form-group">
                        <label for="reg-username">用户名（3-30 字符，字母数字下划线）</label>
                        <input type="text" id="reg-username" class="form-input" required autofocus minlength="3" maxlength="30" pattern="[a-zA-Z0-9_]+">
                    </div>
                    <div class="form-group">
                        <label for="reg-email">邮箱</label>
                        <input type="email" id="reg-email" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label for="reg-password">密码（6-128 字符）</label>
                        <input type="password" id="reg-password" class="form-input" required minlength="6" maxlength="128">
                    </div>
                    <div id="reg-error" class="form-error" style="display:none"></div>
                    <button type="submit" class="btn">注册并登录</button>
                </form>
                <p class="auth-switch">
                    已有账号？<a href="#/login">立即登录</a>
                </p>
            </div>
        </div>
    `;

    const form = document.getElementById('register-form');
    const errorEl = document.getElementById('reg-error');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorEl.style.display = 'none';
        const btn = form.querySelector('button');
        btn.disabled = true;
        btn.textContent = '注册中...';

        try {
            const data = await api.register(
                document.getElementById('reg-username').value,
                document.getElementById('reg-email').value,
                document.getElementById('reg-password').value
            );
            state.setCurrentUser(data.user);
            showToast('注册成功，欢迎！');
            navigate('#/notes');
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.style.display = 'block';
        } finally {
            btn.disabled = false;
            btn.textContent = '注册并登录';
        }
    });
}
