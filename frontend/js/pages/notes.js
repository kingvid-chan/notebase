/**
 * Notes list page.
 */

import { api } from '../api.js';
import { state } from '../state.js';
import { renderNoteList } from '../components/note-list.js';
import { renderSearchBar } from '../components/search-bar.js';
import { showToast } from '../components/toast.js';

export async function renderNotesPage() {
    if (!state.isLoggedIn) {
        const { navigate } = await import('../router.js');
        navigate('#/login');
        return;
    }

    const main = document.getElementById('app-main');

    // Placeholder while loading
    main.innerHTML = '<div class="loading">加载中...</div>';

    let currentQuery = '';

    async function loadNotes(q = '') {
        try {
            const data = await api.listNotes({ q });
            const labels = await api.listLabels();

            main.innerHTML = '';
            main.appendChild(renderSearchBar(q, async (newQ) => {
                currentQuery = newQ;
                await loadNotes(newQ);
            }));

            // Label filter chips
            if (labels.tags && labels.tags.length > 0) {
                const filterDiv = document.createElement('div');
                filterDiv.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;';
                labels.tags.forEach(l => {
                    const chip = document.createElement('span');
                    chip.className = 'label';
                    chip.style.cursor = 'pointer';
                    chip.textContent = l.name;
                    chip.addEventListener('click', async () => {
                        try {
                            const filtered = await api.listNotes({ tag: l.name });
                            _refreshList(filtered.notes);
                        } catch (err) {
                            showToast(err.message, 'error');
                        }
                    });
                    filterDiv.appendChild(chip);
                });
                main.appendChild(filterDiv);
            }

            const listDiv = document.createElement('div');
            listDiv.id = 'notes-list';
            listDiv.innerHTML = renderNoteList(data.notes);
            main.appendChild(listDiv);
        } catch (err) {
            main.innerHTML = `<div class="empty-state"><h3>加载失败</h3><p>${err.message}</p></div>`;
        }
    }

    function _refreshList(notes) {
        const div = document.getElementById('notes-list');
        if (div) div.innerHTML = renderNoteList(notes);
    }

    await loadNotes('');
}
