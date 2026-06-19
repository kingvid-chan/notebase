/**
 * Label picker component — select/deselect labels, create new ones.
 */

import { api } from '../api.js';
import { showToast } from './toast.js';
import { renderLabelList } from './label-badge.js';

export function renderLabelPicker(allLabels, selectedLabelIds, onChange) {
    const container = document.createElement('div');
    container.className = 'label-picker';

    // Existing labels as toggle buttons
    const selected = new Set(selectedLabelIds || []);

    const labelList = document.createElement('div');
    labelList.className = 'label-list';

    allLabels.forEach(l => {
        const el = document.createElement('span');
        el.className = `label ${selected.has(l.id) ? '' : 'label-outline'}`;
        el.style.cssText = selected.has(l.id) ? '' : 'background: #e5e7eb; color: #374151; cursor: pointer;';
        el.textContent = l.name;
        el.style.cursor = 'pointer';
        el.addEventListener('click', () => {
            if (selected.has(l.id)) {
                selected.delete(l.id);
            } else {
                selected.add(l.id);
            }
            onChange([...selected]);
            // Re-render
            container.replaceWith(renderLabelPicker(allLabels, [...selected], onChange));
        });
        labelList.appendChild(el);
    });

    container.appendChild(labelList);

    // New label input
    const inputGroup = document.createElement('div');
    inputGroup.style.cssText = 'display:flex;gap:4px;';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'form-input';
    input.placeholder = '新建...';
    input.style.cssText = 'width:80px;padding:2px 6px;font-size:12px;';

    const addBtn = document.createElement('button');
    addBtn.className = 'btn btn-sm';
    addBtn.textContent = '+';

    addBtn.addEventListener('click', async () => {
        const name = input.value.trim();
        if (!name) return;
        try {
            const resp = await api.createLabel(name);
            const newLabel = resp.tags ? resp.tags[0] : resp;
            showToast('标签已创建');
            onChange([...selected, newLabel.id]);
            // Reload all labels from server and re-render
            const all = await api.listLabels();
            container.replaceWith(renderLabelPicker(
                all.tags, [...selected, newLabel.id], onChange
            ));
        } catch (err) {
            showToast(err.message, 'error');
        }
    });

    inputGroup.appendChild(input);
    inputGroup.appendChild(addBtn);
    container.appendChild(inputGroup);

    return container;
}
