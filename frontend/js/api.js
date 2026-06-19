/**
 * HTTP 请求封装：Fetch API + JSON 序列化 + 错误处理。
 */

const BASE = window.__BASE_PATH__ || '/projects/notebase';
const API = `${BASE}/api`;

class ApiError extends Error {
    constructor(status, detail) {
        super(detail || `请求失败 (${status})`);
        this.status = status;
        this.detail = detail;
    }
}

async function request(method, path, body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
    };
    if (body && method !== 'GET') {
        opts.body = JSON.stringify(body);
    }

    let resp;
    try {
        resp = await fetch(`${API}${path}`, opts);
    } catch (err) {
        throw new ApiError(0, '网络连接失败');
    }

    // No content
    if (resp.status === 204) return null;

    // 公开分享页面返回 HTML，非 JSON
    const ct = resp.headers.get('content-type') || '';
    if (ct.includes('text/html')) {
        return { html: await resp.text() };
    }

    const data = await resp.json().catch(() => null);

    if (!resp.ok) {
        const detail = data?.detail || data?.error?.message || `请求失败 (${resp.status})`;
        throw new ApiError(resp.status, detail);
    }

    return data;
}

export const api = {
    // Auth
    async register(username, email, password) {
        return request('POST', '/auth/register', { username, email, password });
    },
    async login(username, password) {
        return request('POST', '/auth/login', { username, password });
    },
    async logout() {
        return request('POST', '/auth/logout');
    },
    async me() {
        return request('GET', '/auth/me');
    },

    // Notes
    async listNotes(params = {}) {
        const qs = new URLSearchParams();
        if (params.q) qs.set('q', params.q);
        if (params.tag) qs.set('tag', params.tag);
        if (params.page) qs.set('page', params.page);
        if (params.limit) qs.set('limit', params.limit);
        const s = qs.toString();
        return request('GET', `/notes${s ? '?' + s : ''}`);
    },
    async createNote(title, content_markdown, tag_ids = []) {
        return request('POST', '/notes', { title, content_markdown, tag_ids });
    },
    async getNote(id) {
        return request('GET', `/notes/${id}`);
    },
    async updateNote(id, data) {
        return request('PUT', `/notes/${id}`, data);
    },
    async deleteNote(id) {
        return request('DELETE', `/notes/${id}`);
    },

    // Labels
    async listLabels() {
        return request('GET', '/tags');
    },
    async createLabel(name) {
        return request('POST', '/tags', { name });
    },
    async deleteLabel(id) {
        return request('DELETE', `/tags/${id}`);
    },
    async addNoteLabel(noteId, tag_id) {
        return request('POST', `/notes/${noteId}/tags`, { tag_id });
    },
    async removeNoteLabel(noteId, tag_id) {
        return request('DELETE', `/notes/${noteId}/tags/${tag_id}`);
    },

    // Share
    async createShareLink(noteId, expires_at = null) {
        return request('POST', `/notes/${noteId}/share`, { expires_at });
    },
    async listShareLinks(noteId) {
        return request('GET', `/notes/${noteId}/shares`);
    },
    async revokeShareLink(noteId, shareId) {
        return request('DELETE', `/notes/${noteId}/share/${shareId}`);
    },
};

export { ApiError };
