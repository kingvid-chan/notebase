/**
 * Label badge component — renders a list of label badges.
 */

export function renderLabelList(labels, onRemove = null) {
    if (!labels || labels.length === 0) return '';
    return `<div class="label-list">${labels.map(l => {
        const removeBtn = onRemove
            ? `<span class="label-remove" data-label-id="${l.id}">&times;</span>`
            : '';
        return `<span class="label">${l.name}${removeBtn}</span>`;
    }).join('')}</div>`;
}

/**
 * Attach remove handlers for label badges with remove buttons.
 */
export function attachLabelRemoveHandlers(container, onRemove) {
    if (!onRemove) return;
    container.querySelectorAll('.label-remove').forEach(el => {
        el.addEventListener('click', () => {
            const id = parseInt(el.dataset.labelId);
            onRemove(id);
        });
    });
}
