/**
 * Share panel component — manage share links for a note.
 */

import { api } from '../api.js';

export function renderSharePanel(noteId, shares, onRefresh) {
    const panel = document.createElement('div');
    panel.className = 'share-panel';
    panel.innerHTML = `
        <h3>🔗 公开分享</h3>
        <div class="share-links" id="share-links"></div>
        <button class="btn btn-sm" id="btn-create-share">生成分享链接</button>
    `;

    const linksDiv = panel.querySelector('#share-links');
    _renderLinks(linksDiv, noteId, shares, onRefresh);

    panel.querySelector('#btn-create-share').addEventListener('click', async () => {
        try {
            await api.createShareLink(noteId);
            onRefresh();
        } catch (err) {
            alert(err.message);
        }
    });

    return panel;
}

function _renderLinks(container, noteId, shares, onRefresh) {
    if (!shares || shares.length === 0) {
        container.innerHTML = '<p style="color:#6b7280;font-size:14px">暂无分享链接</p>';
        return;
    }

    const BASE = window.__BASE_PATH__ || '/projects/notebase';

    container.innerHTML = shares.map(s => {
        const url = `${location.origin}${BASE}/share/${s.token}`;
        const expired = s.expires_at && new Date(s.expires_at) < new Date();
        return `<div class="share-link-row">
            <span class="share-url">${url}</span>
            ${expired ? '<span style="color:#dc2626;font-size:12px">已过期</span>' : ''}
            <button class="btn btn-sm btn-danger" data-share-id="${s.id}">撤销</button>
        </div>`;
    }).join('');

    container.querySelectorAll('.btn-danger').forEach(btn => {
        btn.addEventListener('click', async () => {
            const sid = parseInt(btn.dataset.shareId);
            if (!confirm('确定撤销此分享链接？')) return;
            try {
                await api.revokeShareLink(noteId, sid);
                onRefresh();
            } catch (err) {
                alert(err.message);
            }
        });
    });
}
