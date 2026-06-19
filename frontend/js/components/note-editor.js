/**
 * Note editor component — split-pane Markdown editing + live preview.
 */

export function renderEditor(title = '', content = '') {
    const container = document.createElement('div');
    container.innerHTML = `
        <div class="editor-container">
            <div class="editor-pane editor-pane-left">
                <textarea id="editor-textarea" class="form-input" placeholder="在此输入 Markdown 内容...">${_escape(content)}</textarea>
            </div>
            <div class="editor-pane editor-pane-right">
                <div id="editor-preview" class="note-content"></div>
            </div>
        </div>
    `;

    const textarea = container.querySelector('#editor-textarea');
    const preview = container.querySelector('#editor-preview');

    function updatePreview() {
        if (typeof marked !== 'undefined') {
            preview.innerHTML = marked.parse(textarea.value, { breaks: true });
        } else {
            preview.innerHTML = '<p class="form-error">marked.js 加载中...</p>';
        }
    }

    textarea.addEventListener('input', updatePreview);
    updatePreview(); // initial render

    return {
        element: container,
        getContent() { return textarea.value; },
        getTitle() { return document.getElementById('note-title-input')?.value || ''; },
        updatePreview,
    };
}

function _escape(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
