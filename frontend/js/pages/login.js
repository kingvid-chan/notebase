/**
 * Login page.
 */

import { api } from '../api.js';
import { state } from '../state.js';
import { navigate } from '../router.js';
import { showToast } from '../components/toast.js';

export async function renderLoginPage() {
    if (state.isLoggedIn) {
        navigate('#/notes');
        return;
    }

    const main = document.getElementById('app-main');
    main.innerHTML = `
        <div class="auth-page">
            <div class="auth-card">
                <h2>登录 Notebase</h2>
                <form id="login-form">
                    <div class="form-group">
                        <label for="login-username">用户名</label>
                        <input type="text" id="login-username" class="form-input" required autofocus>
                    </div>
                    <div class="form-group">
                        <label for="login-password">密码</label>
                        <input type="password" id="login-password" class="form-input" required>
                    </div>
                    <div id="login-error" class="form-error" style="display:none"></div>
                    <button type="submit" class="btn">登录</button>
                </form>
                <p class="auth-switch">
                    没有账号？<a href="#/register">立即注册</a>
                </p>
                <p style="text-align:center;margin-top:12px;font-size:12px;color:#9ca3af">
                    演示账号：alice / demo123 或 bob / demo123
                </p>
            </div>
        </div>
    `;

    const form = document.getElementById('login-form');
    const errorEl = document.getElementById('login-error');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        errorEl.style.display = 'none';
        const btn = form.querySelector('button');
        btn.disabled = true;
        btn.textContent = '登录中...';

        try {
            const data = await api.login(
                document.getElementById('login-username').value,
                document.getElementById('login-password').value
            );
            state.setCurrentUser(data.user);
            showToast('登录成功');
            navigate('#/notes');
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.style.display = 'block';
        } finally {
            btn.disabled = false;
            btn.textContent = '登录';
        }
    });
}
