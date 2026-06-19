/**
 * Search bar component — FTS5 full-text search input.
 */

export function renderSearchBar(currentQuery, onSearch) {
    const form = document.createElement('form');
    form.className = 'notes-toolbar';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'form-input';
    input.placeholder = '搜索笔记标题和内容...';
    input.value = currentQuery || '';
    form.appendChild(input);

    if (currentQuery) {
        const clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'btn btn-sm btn-outline';
        clearBtn.textContent = '清除';
        clearBtn.addEventListener('click', () => onSearch(''));
        form.appendChild(clearBtn);
    }

    form.addEventListener('submit', (e) => {
        e.preventDefault();
        onSearch(input.value.trim());
    });

    return form;
}
