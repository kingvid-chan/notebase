/**
 * 全局状态管理（发布-订阅模式）。
 */

const _state = {
    currentUser: null,       // { id, username, email, created_at } | null
    authChecked: false,      // 是否已检查过登录状态
};

const _listeners = new Set();

export const state = {
    get currentUser() { return _state.currentUser; },
    get isLoggedIn() { return !!_state.currentUser; },

    setCurrentUser(user) {
        _state.currentUser = user;
        _state.authChecked = true;
        _notify();
    },

    clearUser() {
        _state.currentUser = null;
        _state.authChecked = true;
        _notify();
    },

    onChange(fn) {
        _listeners.add(fn);
        return () => _listeners.delete(fn);
    },

    get authChecked() { return _state.authChecked; },
};

function _notify() {
    _listeners.forEach(fn => fn(_state));
}
