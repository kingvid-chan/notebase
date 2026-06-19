/**
 * Hash 路由引擎。
 *
 * 路由表：
 *   #/login    → /login  (无需登录)
 *   #/register → /register (无需登录)
 *   #/notes    → /notes  (需登录，默认首页)
 *   #/notes/new → /notes/new (需登录)
 *   #/notes/:id → /notes/:id (需登录)
 */

const _routes = [];
let _currentCleanup = null;

/**
 * 解析当前 hash，返回 { page, params }。
 */
export function parseHash() {
    const raw = location.hash.slice(1) || '/notes'; // 默认首页
    const [path, ...rest] = raw.split('?');
    const parts = path.split('/').filter(Boolean);

    // /notes/123 → page=notes-detail, params={id: "123"}
    if (parts[0] === 'notes' && parts[1] === 'new') {
        return { page: 'notes-new', params: {} };
    }
    if (parts[0] === 'notes' && parts[1] && !isNaN(parts[1])) {
        return { page: 'notes-detail', params: { id: parts[1] } };
    }
    if (parts[0] === 'notes') {
        return { page: 'notes', params: {} };
    }

    return { page: parts[0] || 'notes', params: {} };
}

/**
 * 注册路由：page name → render function。
 */
export function on(page, renderFn) {
    _routes.push({ page, renderFn });
}

/**
 * 导航到 hash 路径。
 */
export function navigate(hash) {
    if (location.hash === hash) {
        // 强制刷新同页
        location.hash = '';
        setTimeout(() => { location.hash = hash; }, 0);
    } else {
        location.hash = hash;
    }
}

/**
 * 启动路由器：注册 hashchange 事件并渲染当前页面。
 */
export async function startRouter() {
    window.addEventListener('hashchange', () => _render());
    await _render();
}

async function _render() {
    // 清理上一页
    if (_currentCleanup) {
        try { _currentCleanup(); } catch (e) { /* ignore */ }
        _currentCleanup = null;
    }

    const { page, params } = parseHash();
    const route = _routes.find(r => r.page === page);

    if (!route) {
        navigate('#/notes');
        return;
    }

    try {
        const cleanup = await route.renderFn(params);
        if (typeof cleanup === 'function') _currentCleanup = cleanup;
    } catch (err) {
        console.error(`Route [${page}] error:`, err);
    }

    _updateNav(page);
}

function _updateNav(page) {
    document.querySelectorAll('.nav-link').forEach(el => {
        el.classList.toggle('active', el.dataset.page === page);
    });
}
