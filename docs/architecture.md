# 笔记管理系统 当前架构

> 迭代: 0.0.1 | 日期: 2026-06-19 | ADR: docs/decisions/001-technical-plan.md

## 系统目标与边界

notebase 是一个单人笔记管理系统，支持用户注册登录、Markdown 笔记的增删改查、标签分类、全文搜索和公开分享链接。

**本版范围**：
- 用户注册/登录/登出（Session Cookie 认证）
- 笔记 CRUD（服务端 Markdown→HTML 渲染 + bleach XSS 清洗）
- 标签管理（用户级标签，笔记多对多关联，按标签筛选）
- 全文搜索（SQLite FTS5）
- 公开分享（随机 token 链接，过期时间，只读页面）
- 权限隔离（用户仅访问自己的笔记和标签）

**明确不做**：OAuth/第三方登录、协作编辑、文件附件上传、邮件验证/密码重置、移动端原生 App。

## 技术栈与选择理由

| 层面 | 选择 | 理由 |
|------|------|------|
| 语言/框架 | Python 3.12+ + FastAPI | 异步支持、自动 OpenAPI 文档、类型安全 |
| ORM | SQLAlchemy 2.0 (async) | 成熟稳定、参数化查询防注入 |
| 数据库 | SQLite (aiosqlite) | 零配置、文件级部署、0.0.1 演示阶段足够 |
| 认证 | itsdangerous 签名 Cookie | 无外部依赖；HttpOnly / Secure / SameSite=Lax |
| 密码哈希 | passlib[bcrypt] | 行业标准 bcrypt 算法 |
| Markdown 渲染 | Python-Markdown + bleach 清洗 | 服务端渲染存储；bleach 白名单防 XSS |
| 模板引擎 | Jinja2 (FastAPI 内置) | SPA 外壳 + 公开分享页 |
| HTTP 服务器 | Uvicorn | FastAPI 官方推荐 |
| 前端架构 | Vanilla JS SPA (ES Modules) | 无构建步骤、零依赖打包、Hash 路由 |
| 前端 Markdown | marked.js v15+ (CDN) | 客户端实时预览 |
| CSS | 自建响应式 CSS (Grid/Flexbox) | 零外部依赖 |
| 测试 | pytest + pytest-asyncio + httpx | 异步测试支持、内存 SQLite |

## 模块职责与依赖

```
┌─ backend/app.py ── FastAPI 工厂, 路由挂载, 中间件, 静态文件 ─┐
│                                                                │
│  ┌─ backend/middleware.py ───────────────────────────────┐     │
│  │  SessionMiddleware: Cookie → request.state.current_user_id │
│  │  CacheControlMiddleware: HTML→no-cache, JSON→no-store      │
│  └───────────────────────────────────────────────────────┘     │
│                                                                │
│  ┌─ routers/auth.py ──── POST register/login/logout, GET me ──┤
│  │  └─ services/auth.py ── register_user, login_user          │
│  │  └─ services/session.py ── sign_session, unsign_session    │
│  │                                                             │
│  ├─ routers/notes.py ─── CRUD: POST/GET/PUT/DELETE /notes ────┤
│  │  └─ services/note.py ── create/get/update/delete/list/search│
│  │  └─ services/markdown.py ── Python-Markdown + bleach 清洗  │
│  │                                                             │
│  ├─ routers/tags.py ──── CRUD: POST/GET/DELETE /tags ─────────┤
│  │  └─ services/tag.py ── create/get/delete/tag, 关联管理     │
│  │                                                             │
│  ├─ routers/share.py ─── POST share, GET shares, DELETE share │
│  │  └─ services/share.py ── create/delete/get_note_by_token   │
│  │                                                             │
│  ├─ routers/pages.py ─── SPA 入口 / (index.html)              │
│  │                     └─ 公开分享页 /share/{token}            │
│  │                                                             │
│  └─ dependencies.py ── get_current_user, get_optional_user     │
│                                                                │
├─ backend/models/ ── User, Note, Tag, NoteTag, ShareLink        │
├─ backend/schemas/ ── Pydantic request/response 模型            │
├─ backend/database.py ── async engine, session, Base            │
├─ backend/config.py ── Settings (Pydantic, .env 读取)           │
└─ backend/seed.py ── 演示数据初始化 (alice, bob + 示例笔记)     │

frontend/
├─ js/app.js ─── 入口：初始化路由、全局状态
├─ js/router.js ─── Hash 路由引擎 (hashchange 监听)
├─ js/api.js ─── Fetch API 封装、错误拦截 (401→重定向登录)
├─ js/state.js ─── 全局状态管理
├─ js/pages/ ─── login.js, register.js, notes.js, note-detail.js
├─ js/components/ ─── note-list, note-editor, label-badge,
│                      label-picker, search-bar, share-panel, toast
└─ css/style.css ─── 响应式布局 (CSS Grid + Flexbox)
```

## 数据流、状态流与外部接口

### 认证流

```
用户 POST /api/auth/login → auth_service.login_user
  → bcrypt 验证密码
  → sign_session(user.id) 生成签名 token
  → Response.set_cookie("session", token, HttpOnly, SameSite=Lax, path=BASE_PATH)
  → 后续请求: SessionMiddleware 解析 Cookie → request.state.current_user_id
  → get_current_user 依赖注入加载 User 对象
```

### 笔记数据流

```
创建: POST /api/notes {title, content_markdown}
  → markdown_service.render() → bleach.clean() → content_html
  → Note(user_id, title, content_markdown, content_html) INSERT
  → 返回 Note + HTML

更新: PUT /api/notes/{id} {content_markdown}
  → 重新渲染 HTML → UPDATE
  → 返回更新后的 Note

列表: GET /api/notes?q=xxx&tag=urgent
  → FTS5 MATCH (全文搜索) 或
  → JOIN note_tags + tags (标签筛选)
  → 分页返回

搜索: FTS5 虚拟表 notes_fts(title, content_markdown)
  → MATCH '"keyword"' → JOIN notes ORDER BY rank
```

### 分享数据流

```
创建: POST /api/notes/{id}/share → generate_token(32 bytes url-safe)
  → ShareLink(note_id, token, expires_at) INSERT
  → 返回 token

公开访问: GET /share/{token}
  → get_note_by_token(token) → 校验过期
  → 查询 Note → Jinja2 渲染 shared-note.html
  → 返回渲染后的 HTML（无需登录）

撤销: DELETE /api/notes/{id}/share/{sid}
  → 校验笔记所有权 → DELETE share_link
```

### 外部接口

- 无外部 API 依赖
- marked.js 从 CDN 加载，本地副本兜底 (`frontend/lib/marked.min.js`)
- 所有资源在 `/projects/notebase/` 前缀下

## 测试策略

### 测试框架

- pytest + pytest-asyncio + httpx (AsyncClient)
- 内存 SQLite (sqlite+aiosqlite://) 隔离测试
- conftest.py 提供 async client, db session, demo user fixtures

### 覆盖范围

| 文件 | 测试数 | 覆盖 |
|------|--------|------|
| tests/test_auth.py | 9 | 注册/登录/登出/权限拦截/Cache-Control |
| tests/test_notes.py | 8 | CRUD + 权限隔离 + 全文搜索 + 标签筛选 |
| tests/test_tags.py | 6 | 标签 CRUD + 笔记关联 + 用户隔离 |
| tests/test_share.py | 9 | 分享生成/列出/公开访问/撤销/权限隔离 |

### 运行

```bash
cd /Users/cqw/外部需求/proj-bd3aaa
pytest tests/ -v --tb=short
```

全部 36 项测试，覆盖核心业务流程和权限边界。

## 部署拓扑

### 开发环境

```
Uvicorn (localhost:8000)
  └─ FastAPI app
      ├─ /projects/notebase/api/*   (JSON API)
      ├─ /projects/notebase/static/* (静态文件: CSS, JS)
      ├─ /projects/notebase/share/*  (公开分享页)
      ├─ /projects/notebase/         (SPA 入口)
      └─ /projects/notebase/health   (健康检查)
```

### 生产环境 (Aliyun)

```
Nginx (port 80/443)
  ├─ /projects/notebase/ → proxy_pass http://127.0.0.1:19010
  └─ static assets cached with ?v=0.0.1 tokens

Systemd: notebase.service
  └─ uvicorn backend.app:app --host 127.0.0.1 --port 19010
```

## 安全边界

| 层面 | 措施 |
|------|------|
| 密码存储 | bcrypt (cost=12), passlib |
| 会话 | itsdangerous URLSafeTimedSerializer, 24h 过期, HttpOnly Cookie |
| CSRF | SameSite=Lax Cookie + JSON-only API (无 form POST) |
| XSS | bleach 白名单过滤 Markdown HTML 输出; Jinja2 自动转义 |
| SQL 注入 | SQLAlchemy ORM 参数化查询; FTS5 MATCH 参数化 |
| 权限 | get_current_user 依赖注入校验所有权; 用户隔离 |
| 分享 | secrets.token_urlsafe(32) — 192 bits 熵, 支持 expires_at |
| 密钥 | .env 在 .gitignore; SECRET_KEY 环境变量注入 |

## 已知技术债

| 项目 | 影响 | 计划 |
|------|------|------|
| SQLite 并发写入锁 | 多用户同时写可能报错 | 0.0.2+ 迁移 PostgreSQL |
| datetime.utcnow() 废弃 | Python 3.13 警告 | 后续迁移到 timezone-aware datetime |
| 前端无构建工具 | 模块数增加后加载效率下降 | 0.0.2+ 评估引入 Alpine.js/Vue.js + 构建 |
| 无 HTTPS (演示) | Cookie Secure=false | 生产部署启用 HTTPS |
| 无密码重置 | 演示账号锁死无法恢复 | seed.py 可重置; 0.0.2+ 加入邮件验证 |
| bleach 已 archived | 依赖不再维护 | 0.0.2+ 迁移到 nh3 或替代方案 |

## 关联 ADR 与最近变更

- **ADR-001**: [001-technical-plan.md](decisions/001-technical-plan.md) — 0.0.1 完整技术方案
- **迭代文档**: [iterations/0.0.1.md](iterations/0.0.1.md)
- **最近提交** (iteration/0.0.1):
  - `60e46ea` task-8: cache strategy
  - `9166566` task-7: frontend SPA
  - `a699df3` task-6: share module
  - `e081755` task-5: labels module
  - `ba12d07` task-4: 笔记模块
  - `0e5f5fa` task-3: 认证模块
  - `a00b475` task-2: 数据库模型与种子数据
  - `8e9a1cb` task-1: 项目骨架
