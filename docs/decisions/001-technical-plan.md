# ADR-001: 0.0.1 技术方案

> 状态: accepted | 日期: 2026-06-19 | 迭代: 0.0.1

## 1. 技术栈选择

### 1.1 后端

| 层面 | 选择 | 理由 |
|------|------|------|
| 语言/框架 | Python 3.12 + FastAPI | 迭代文档已指定；异步支持好、自动 OpenAPI 文档、类型安全 |
| ORM | SQLAlchemy 2.0 (async) | 迭代文档已指定；成熟稳定、迁移工具 Alembic 配套 |
| 数据库 | SQLite (aiosqlite) | 迭代文档已指定开发环境；零配置、文件级部署 |
| 认证 | Session + 签名的 Cookie (itsdangerous) | 无需外部依赖；Cookie 携带 `Secure/HttpOnly/SameSite=Lax`；与 Base Path 兼容 |
| 密码哈希 | passlib[bcrypt] | 行业标准 bcrypt 算法 |
| Markdown 渲染 | Python-Markdown + bleach 清洗 | 服务端渲染 HTML 存储；bleach 白名单过滤防 XSS |
| 模板引擎 | Jinja2 (FastAPI 内置) | 下发 SPA 外壳 HTML，注入 base_path 和版本令牌 |
| HTTP 服务器 | Uvicorn | FastAPI 官方推荐 |

### 1.2 前端

| 层面 | 选择 | 理由 |
|------|------|------|
| 架构 | 单页应用 (SPA)，Hash 路由 | 无需服务端路由配合；刷新不丢状态；兼容 `/projects/notebase/` 前缀 |
| 语言/模块 | Vanilla JavaScript (ES Modules) | 无构建步骤、零依赖打包、静态文件直接部署；迭代 0.0.1 规模可控 |
| Markdown 编辑 | 自建 split-pane（textarea + 预览 div） | 避免重量级编辑器依赖；预览使用 marked.js 客户端渲染 |
| Markdown 渲染 | marked.js v15+ (CDN) | 轻量、客户端实时预览；服务端用 Python-Markdown 保证存储一致性 |
| CSS | 自建响应式 CSS | 零外部依赖；通过 CSS Grid/Flexbox 适配桌面和移动端 |
| HTTP 客户端 | Fetch API | 浏览器原生、无依赖 |
| 图标 | 内联 SVG / Unicode | 零外部请求 |

### 1.3 为何不用构建工具

- 迭代 0.0.1 前端规模约 8–12 个 JS 模块，不构成构建必要性
- 无构建步骤 = 无 node_modules、无 webpack/vite 配置、无 sourcemap 泄露
- 静态资源直接通过 FastAPI mount 或 Nginx alias 提供
- 后续迭代可按需引入 Alpine.js / Vue.js + 构建工具

## 2. 数据模型

### 2.1 ER 图（逻辑）

```
User ──1:N──> Note ──1:N──> ShareLink
  │             │
  └──1:N──> Tag─┘ (via NoteTag N:M)
```

### 2.2 表结构

```sql
-- 用户
CREATE TABLE users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL UNIQUE,
    email       TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 笔记
CREATE TABLE notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    content_markdown TEXT NOT NULL DEFAULT '',
    content_html    TEXT NOT NULL DEFAULT '',
    is_public       INTEGER NOT NULL DEFAULT 0,  -- SQLite 无 BOOLEAN
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_notes_user_id ON notes(user_id);
CREATE INDEX idx_notes_updated_at ON notes(updated_at);

-- 标签（用户级别）
CREATE TABLE tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, name)
);
CREATE INDEX idx_tags_user_id ON tags(user_id);

-- 笔记-标签关联
CREATE TABLE note_tags (
    note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    tag_id  INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (note_id, tag_id)
);

-- 分享链接
CREATE TABLE share_links (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id     INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    token       TEXT NOT NULL UNIQUE,
    expires_at  TEXT,  -- NULL = 永不过期
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_share_links_token ON share_links(token);
```

### 2.3 SQLAlchemy 模型

使用 async SQLAlchemy 2.0 style (`DeclarativeBase`, `Mapped` 注解)。所有模型统一时间字段用 `datetime.utcnow` 字符串存储（SQLite 兼容性）。`is_public` 使用 `Integer` 映射为 Python `bool`。

## 3. API 设计

Base URL: `/projects/notebase/api`

### 3.1 认证

| Method | Path | Body | Response | 说明 |
|--------|------|------|----------|------|
| POST | `/auth/register` | `{username, email, password}` | `{user, session_token}` | 注册并自动登录 |
| POST | `/auth/login` | `{username, password}` | `{user, session_token}` | 登录 |
| POST | `/auth/logout` | — | `{ok: true}` | 登出，清除 Cookie |
| GET | `/auth/me` | — | `{user}` | 当前会话用户 |

认证方式：登录后 FastAPI 设置签名的 session Cookie（`session=<signed_token>`），后续请求由中间件从 Cookie 解析 user_id 注入 `request.state.current_user`。依赖注入 `get_current_user` 在需要认证的路由上强制校验。

### 3.2 笔记

| Method | Path | Query/ Body | Response | 说明 |
|--------|------|------------|----------|------|
| GET | `/notes` | `?tag=&q=&page=&limit=` | `{notes: [...], total}` | 列表；tag 按标签名筛选；q 全文搜索 title+content |
| POST | `/notes` | `{title, content_markdown, tags: []}` | `{note}` | 创建；服务端渲染 content_html |
| GET | `/notes/{id}` | — | `{note, tags}` | 单条详情（仅所有者） |
| PUT | `/notes/{id}` | `{title?, content_markdown?, is_public?}` | `{note}` | 更新；重新渲染 content_html |
| DELETE | `/notes/{id}` | — | `{ok: true}` | 删除（级联删除标签关联和分享链接） |

全文搜索：SQLite FTS5 虚拟表，在 `notes.content_markdown` 和 `notes.title` 上建 FTS 索引。搜索 API 使用 FTS5 `MATCH` 语法，返回按相关度排序的结果。

### 3.3 标签

| Method | Path | Body | Response | 说明 |
|--------|------|------|----------|------|
| GET | `/tags` | — | `{tags: [...]}` | 当前用户所有标签 |
| POST | `/tags` | `{name}` | `{tag}` | 创建标签 |
| DELETE | `/tags/{id}` | — | `{ok: true}` | 删除标签（解除关联） |
| POST | `/notes/{id}/tags` | `{tag_id}` | `{ok: true}` | 为笔记添加标签 |
| DELETE | `/notes/{id}/tags/{tag_id}` | — | `{ok: true}` | 移除笔记标签 |

### 3.4 分享

| Method | Path | Body | Response | 说明 |
|--------|------|------|----------|------|
| POST | `/notes/{id}/share` | `{expires_at?}` | `{share_link}` | 生成分享链接 |
| DELETE | `/notes/{id}/share/{share_id}` | — | `{ok: true}` | 撤销分享链接 |
| GET | `/notes/{id}/shares` | — | `{share_links: [...]}` | 笔记的所有分享链接 |

### 3.5 公开访问

| Method | Path | Response | 说明 |
|--------|------|----------|------|
| GET | `/share/{token}` | 渲染后的 HTML 页面（只读） | 无需登录；展示渲染后的笔记 |

公开分享页面使用单独的轻量 HTML 模板，不加载 SPA 框架，只渲染笔记内容和元信息。

### 3.6 标准响应格式

```json
// 成功
{ "ok": true, "data": { ... } }

// 错误
{ "ok": false, "error": { "code": "NOT_FOUND", "message": "笔记不存在" } }
```

HTTP 状态码：200(成功), 201(创建), 400(参数错误), 401(未登录), 403(无权限), 404(不存在), 409(冲突), 422(校验失败), 500(服务错误)。

## 4. 前端路由

### 4.1 Hash 路由表

| Hash | 页面 | 需要登录 | 说明 |
|------|------|---------|------|
| `#/login` | 登录页 | 否 | 重定向已登录用户 |
| `#/register` | 注册页 | 否 | 重定向已登录用户 |
| `#/notes` | 笔记列表 | 是 | 默认首页；支持标签筛选 & 搜索 |
| `#/notes/new` | 新建笔记 | 是 | Markdown 编辑 + 实时预览 |
| `#/notes/{id}` | 笔记详情/编辑 | 是 | 编辑模式、标签管理、分享管理 |
| `#/share/{token}` | 公开分享页 | 否 | 服务端渲染的只读页面（非 SPA 路由） |

备注：`#/share/{token}` 虽然列在此处供参考，但实际由服务端 `/projects/notebase/share/{token}` 返回独立 HTML 页面，不走 SPA。

### 4.2 路由实现

`router.js` 监听 `hashchange` 事件，解析 hash 为 `{page, params}`，调用对应页面渲染函数。页面切换时清理上一页事件监听和 DOM。

### 4.3 Base Path 处理

所有 API 请求路径通过全局配置 `BASE_PATH = '/projects/notebase'` 拼接。index.html 由 Jinja2 模板在服务端注入 `window.__BASE_PATH__` 变量。

## 5. 目录结构

```
notebase/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI app 工厂，路由挂载，静态文件，中间件
│   ├── config.py            # 配置类（读取 .env）
│   ├── database.py          # async engine, session factory, Base
│   ├── middleware.py         # Session 解析 + Cache-Control 注入
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── note.py
│   │   ├── tag.py
│   │   ├── note_tag.py
│   │   └── share_link.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py          # 请求/响应 Pydantic 模型
│   │   ├── note.py
│   │   ├── tag.py
│   │   └── share_link.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py          # /api/auth/*
│   │   ├── notes.py         # /api/notes/*
│   │   ├── tags.py          # /api/tags/*
│   │   └── share.py         # /api/share/* + 公开分享页面
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py          # 注册、登录、登出逻辑
│   │   ├── note.py          # 笔记 CRUD + 搜索
│   │   ├── tag.py           # 标签 CRUD + 关联管理
│   │   ├── share.py         # 分享链接生成/验证
│   │   └── markdown.py      # Markdown → HTML 渲染 + bleach 清洗
│   ├── dependencies.py      # FastAPI 依赖注入（get_db, get_current_user）
│   ├── seed.py              # 演示数据初始化脚本
│   └── templates/
│       ├── index.html       # SPA 外壳
│       └── shared-note.html # 公开分享阅读页面
├── frontend/
│   ├── css/
│   │   └── style.css        # 全局样式（响应式）
│   ├── js/
│   │   ├── app.js           # 入口：初始化路由、全局状态
│   │   ├── router.js        # Hash 路由引擎
│   │   ├── api.js           # HTTP 请求封装、错误处理
│   │   ├── state.js         # 全局状态管理（当前用户、笔记列表缓存）
│   │   ├── components/
│   │   │   ├── note-list.js    # 笔记列表组件
│   │   │   ├── note-editor.js  # Markdown 编辑 + 预览
│   │   │   ├── tag-badge.js    # 标签徽章组件
│   │   │   ├── tag-picker.js   # 标签选择/添加组件
│   │   │   ├── search-bar.js   # 搜索栏组件
│   │   │   ├── share-panel.js  # 分享链接管理面板
│   │   │   └── toast.js        # Toast 通知组件
│   │   └── pages/
│   │       ├── login.js
│   │       ├── register.js
│   │       ├── notes.js        # 列表页逻辑
│   │       └── note-detail.js  # 详情/编辑页逻辑
│   └── lib/
│       └── marked.min.js    # marked.js v15 (CDN 备选本地副本)
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Fixtures: async client, test db, demo users
│   ├── test_auth.py         # 注册/登录/登出/权限拦截
│   ├── test_notes.py        # CRUD + 权限隔离
│   ├── test_tags.py         # 标签 CRUD + 关联
│   └── test_share.py        # 分享链接 + 公开访问 + 过期
├── docs/
│   ├── architecture.md
│   ├── runbook.md
│   ├── decisions/
│   │   └── 001-technical-plan.md
│   └── iterations/
│       └── 0.0.1.md
├── evidence/
│   └── claude/
│       ├── technical-plan-0.0.1.json
│       └── handoff-0.0.1.json
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 6. 安全设计

### 6.1 认证与授权

- **密码存储**：bcrypt（cost=12），通过 passlib 实现
- **会话管理**：登录后使用 `itsdangerous.URLSafeTimedSerializer` 签名用户 ID + 过期时间，写入 HttpOnly / Secure / SameSite=Lax Cookie
- **会话过期**：默认 24 小时，可通过配置调整
- **权限隔离**：所有 `/api/notes/*` 端点通过 `get_current_user` 依赖注入校验所有权；用户只能操作自己的笔记和标签
- **分享链接**：使用 `secrets.token_urlsafe(32)` 生成，熵值 192 bits；支持 `expires_at` 过期时间

### 6.2 输入校验

- **Pydantic 模型**：所有请求体由 Pydantic 严格校验（类型、长度、格式）
- **用户名**：3-30 字符，字母数字下划线
- **密码**：6-128 字符
- **邮箱**：Pydantic `EmailStr` 校验
- **笔记标题**：1-200 字符
- **笔记内容**：最大 1MB（适合纯文本 Markdown）

### 6.3 输出编码

- **XSS 防护**：
  - Markdown 渲染后 HTML 经 `bleach` 白名单过滤（允许标签：h1-h6, p, a, img, ul, ol, li, code, pre, blockquote, em, strong, table, thead, tbody, tr, th, td, hr, br）
  - 允许属性：`href`, `src`, `alt`, `title`, `class`
  - 禁止 `<script>`, `<style>`, `on*` 事件属性
  - 所有用户输入在 API JSON 响应中由 FastAPI 自动 JSON 编码
- **HTML 模板**：Jinja2 默认自动转义

### 6.4 CSRF

- SameSite=Lax Cookie 提供基础 CSRF 防护
- API 端点为 JSON-only（非 form-encoded），浏览器同源策略阻止跨站 JSON POST（需 preflight）
- 分享页面只读无状态变更，不涉及 CSRF

### 6.5 SQL 注入

- SQLAlchemy ORM 参数化查询，无原生 SQL 拼接
- FTS5 搜索使用参数化 MATCH

### 6.6 环境安全

- `.env` 已加入 `.gitignore`；公开仓库不含任何密钥
- `SECRET_KEY` 用于签名 session Cookie，通过 `.env` 注入
- SQLite 文件放在项目目录外或配置中指定路径

## 7. 缓存策略（Hermes 验收要求）

| 资源类型 | 策略 | 实现 |
|----------|------|------|
| HTML 文档 | `Cache-Control: no-cache` 真实 HTTP 头 | FastAPI 中间件对所有 `text/html` 响应注入 |
| 静态资源 (CSS/JS) | `?v=0.0.1` 版本令牌 | Jinja2 模板渲染 `<link>`/`<script>` 时拼接版本号 |
| API 响应 | `Cache-Control: no-store` | 防止 JSON 被缓存 |

关键：**HTML 响应头必须由服务器框架层面下发，不能用 `<meta>` 标签代替**。

## 8. 风险缓解

| 风险 | 影响 | 缓解措施 | 残余风险 |
|------|------|----------|----------|
| SQLite 并发写入锁 | 多用户同时写笔记时报错 | WAL 模式 + 重试机制；0.0.1 为演示阶段，并发低 | 生产迁移到 PostgreSQL 解决 |
| Markdown XSS | 分享页面执行恶意脚本 | bleach 白名单过滤；公共分享页不加载 SPA JS | bleach 配置遗漏极端向量 |
| Session Cookie 泄露 | 账户劫持 | HttpOnly + Secure + SameSite=Lax；演示环境无 HTTPS | 本地开发 Secure=false |
| 分享链接被枚举 | 未授权访问笔记 | token 192 bits 随机，暴力枚举不可行 | — |
| 前端 JS 模块加载失败 | 空白页面 | marked.js 本地副本兜底；ES 模块 native 加载 | CDN 不可用但本地副本可用 |
| 无密码重置 | 演示账号锁死 | seed.py 可重置演示数据；至少 2 个预设账号 | 真实用户无法重置 |

## 9. 自测策略

### 9.1 测试范围

```python
# test_auth.py
- test_register_success          # 注册成功，返回用户信息 + 设置 Cookie
- test_register_duplicate        # 重复用户名/邮箱返回 409
- test_login_success             # 登录成功
- test_login_wrong_password      # 密码错误返回 401
- test_logout                    # 登出清除 Cookie
- test_me_authenticated          # 已登录获取当前用户
- test_me_unauthenticated        # 未登录返回 401

# test_notes.py
- test_create_note               # 创建笔记，HTML 自动渲染
- test_list_notes                # 列出当前用户笔记
- test_get_note                  # 获取单条笔记
- test_update_note               # 更新笔记内容，HTML 重新渲染
- test_delete_note               # 删除笔记
- test_cannot_access_others_note # 权限隔离：用户 A 无法访问用户 B 的笔记
- test_search_notes              # FTS5 全文搜索
- test_filter_by_tag             # 按标签筛选

# test_tags.py
- test_create_tag
- test_list_tags
- test_delete_tag
- test_add_tag_to_note
- test_remove_tag_from_note
- test_tag_isolation             # 用户标签隔离

# test_share.py
- test_create_share_link
- test_access_shared_note        # 公开访问渲染后笔记
- test_shared_note_readonly      # 公开页面无编辑功能
- test_invalid_share_token       # 无效 token 返回 404
- test_expired_share_link        # 过期链接拒绝访问
- test_delete_share_link
```

### 9.2 运行方式

```bash
conda activate codingagent
cd /Users/cqw/外部需求/proj-bd3aaa
pytest tests/ -v --tb=short
```

## 10. 环境变量 (.env.example)

```env
# 基础配置
SECRET_KEY=change-me-to-random-string
DATABASE_URL=sqlite+aiosqlite:///./notebase.db
BASE_PATH=/projects/notebase
VERSION=0.0.1

# 演示账号（seed.py 使用）
DEMO_USER1=alice
DEMO_PASS1=demo123
DEMO_USER2=bob
DEMO_PASS2=demo123

# 日志
LOG_LEVEL=INFO
```

## 11. 实施任务概览

按依赖关系排列：

1. **项目骨架**：目录结构、`requirements.txt`、`.env.example`、配置模块
2. **数据库**：models 定义、database.py、seed.py（含 FTS5 虚拟表和演示数据）
3. **认证模块**：auth 路由和服务、中间件、Session Cookie、依赖注入
4. **笔记模块**：笔记 CRUD 路由和服务、Markdown 渲染、FTS5 搜索
5. **标签模块**：标签 CRUD 和笔记关联路由
6. **分享模块**：分享链接生成/验证、公开访问页面模板
7. **前端**：SPA 外壳、路由、页面、组件、CSS
8. **缓存策略**：版本令牌注入 HTML、Cache-Control 中间件
9. **自测**：pytest 覆盖全部核心流程
10. **文档同步**：architecture.md、runbook.md 完整化
