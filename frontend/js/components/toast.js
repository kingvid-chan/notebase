/**
 * Toast 通知组件。
 */

let _container = null;

function getContainer() {
    if (!_container) {
        _container = document.getElementById('toast-container');
    }
    return _container;
}

export function showToast(message, type = 'success', duration = 3000) {
    const container = getContainer();
    if (!container) return;

    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = message;
    container.appendChild(el);

    setTimeout(() => {
        el.style.opacity = '0';
        el.style.transition = 'opacity .25s';
        setTimeout(() => el.remove(), 250);
    }, duration);
}
