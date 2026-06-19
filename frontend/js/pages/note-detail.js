/**
 * Note detail / edit page (and new note page).
 */

import { api } from '../api.js';
import { state } from '../state.js';
import { navigate } from '../router.js';
import { showToast } from '../components/toast.js';
import { renderEditor } from '../components/note-editor.js';
import { renderLabelList, attachLabelRemoveHandlers } from '../components/label-badge.js';
import { renderLabelPicker } from '../components/label-picker.js';
import { renderSharePanel } from '../components/share-panel.js';

export async function renderNoteNewPage() {
    if (!state.isLoggedIn) { navigate('#/login'); return; }
    _renderNoteEditor(null);
}

export async function renderNoteDetailPage(params) {
    if (!state.isLoggedIn) { navigate('#/login'); return; }

    const main = document.getElementById('app-main');
    main.innerHTML = '<div class="loading">加载中...</div>';

    try {
        const data = await api.getNote(params.id);
        _renderNoteEditor(data);
    } catch (err) {
        main.innerHTML = `<div class="empty-state"><h3>笔记不存在</h3><p>${err.message}</p></div>`;
    }
}

async function _renderNoteEditor(noteData) {
    const main = document.getElementById('app-main');
    const isNew = !noteData;
    const note = noteData?.note || {};
    const existingLabels = noteData?.labels || [];

    main.innerHTML = `
        <div class="note-meta">
            <input type="text" id="note-title-input" class="form-input" placeholder="笔记标题" value="${_esc(isNew ? '' : note.title)}" maxlength="200">
        </div>
        <div id="editor-container"></div>
        <div style="margin-top:16px;display:flex;gap:8px;align-items:center;">
            <button class="btn" id="btn-save">${isNew ? '创建' : '保存'}</button>
            ${!isNew ? '<button class="btn btn-danger" id="btn-delete">删除</button>' : ''}
            ${!isNew ? `<label style="font-size:14px;cursor:pointer;display:flex;align-items:center;gap:4px;">
                <input type="checkbox" id="cb-public" ${note.is_public ? 'checked' : ''}> 公开笔记
            </label>` : ''}
        </div>
        <div id="label-section">${renderLabelList(existingLabels, !isNew ? onLabelRemove : null)}</div>
        <div id="label-picker-section"></div>
        ${!isNew ? '<div id="share-section"></div>' : ''}
    `;

    // Editor
    const editorContainer = document.getElementById('editor-container');
    const editor = renderEditor(isNew ? '' : note.title, isNew ? '' : note.content_markdown);
    editorContainer.appendChild(editor.element);

    // Label picker
    let allLabels = [];
    let selectedLabelIds = existingLabels.map(l => l.id);
    try { const resp = await api.listLabels(); allLabels = resp.tags || []; } catch (_) {}

    const pickerSection = document.getElementById('label-picker-section');
    if (pickerSection) {
        const picker = renderLabelPicker(allLabels, selectedLabelIds, (ids) => {
            selectedLabelIds = ids;
        });
        pickerSection.appendChild(picker);
    }

    // Share section
    if (!isNew && note.id) {
        const shareSection = document.getElementById('share-section');
        await loadSharePanel(shareSection, note.id);
    }

    // Save button
    document.getElementById('btn-save').addEventListener('click', async () => {
        const title = document.getElementById('note-title-input').value.trim();
        if (!title) { showToast('请输入标题', 'error'); return; }

        const content_markdown = editor.getContent();
        const btn = document.getElementById('btn-save');
        btn.disabled = true;
        btn.textContent = '保存中...';

        try {
            if (isNew) {
                const resp = await api.createNote(title, content_markdown, selectedLabelIds);
                showToast('笔记已创建');
                navigate(`#/notes/${resp.note.id}`);
            } else {
                const isPublic = document.getElementById('cb-public')?.checked ?? false;
                const resp = await api.updateNote(note.id, {
                    title, content_markdown,
                    is_public: isPublic,
                });
                // Update labels: remove all then re-add
                for (const l of existingLabels) {
                    await api.removeNoteLabel(note.id, l.id).catch(() => {});
                }
                for (const tid of selectedLabelIds) {
                    await api.addNoteLabel(note.id, tid).catch(() => {});
                }
                showToast('笔记已保存');
                // Refresh
                _renderNoteEditor(resp);
            }
        } catch (err) {
            showToast(err.message, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = isNew ? '创建' : '保存';
        }
    });

    // Delete button
    const btnDelete = document.getElementById('btn-delete');
    if (btnDelete) {
        btnDelete.addEventListener('click', async () => {
            if (!confirm('确定删除这条笔记？此操作不可撤销。')) return;
            try {
                await api.deleteNote(note.id);
                showToast('笔记已删除');
                navigate('#/notes');
            } catch (err) {
                showToast(err.message, 'error');
            }
        });
    }
}

async function onLabelRemove(labelId) {
    // handled by _renderNoteEditor re-render
}

async function loadSharePanel(section, noteId) {
    try {
        const resp = await api.listShareLinks(noteId);
        const panel = renderSharePanel(noteId, resp.share_links, () => loadSharePanel(section, noteId));
        section.innerHTML = '';
        section.appendChild(panel);
    } catch (err) {
        section.innerHTML = `<p style="color:#6b7280;font-size:14px">无法加载分享信息</p>`;
    }
}

function _esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}
