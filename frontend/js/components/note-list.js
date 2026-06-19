/**
 * Note list component — renders a list of note cards.
 */

import { renderLabelList } from './label-badge.js';

function _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function _snippet(html, maxLen = 120) {
    const div = document.createElement('div');
    div.innerHTML = html;
    const text = (div.textContent || '').trim();
    return text.length > maxLen ? text.slice(0, maxLen) + '...' : text;
}

export function renderNoteList(notes) {
    if (!notes || notes.length === 0) {
        return `<div class="empty-state">
            <h3>还没有笔记</h3>
            <p>点击「新建」开始写作吧 ✍️</p>
            <a href="#/notes/new" class="btn" style="margin-top:12px">新建笔记</a>
        </div>`;
    }

    return `<div class="note-list">${notes.map(n => `
        <a href="#/notes/${n.id}" class="note-card">
            <div class="note-card-title">${_escapeHtml(n.title)}</div>
            <div class="note-card-meta">
                <span>更新于 ${(n.updated_at || '').slice(0, 10)}</span>
                ${n.is_public ? '<span>🌐 公开</span>' : ''}
            </div>
            <div class="note-card-snippet">${_snippet(n.content_html)}</div>
        </a>
    `).join('')}</div>`;
}
