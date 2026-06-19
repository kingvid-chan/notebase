# 笔记管理系统 运行手册

> 迭代: 0.0.1 | 项目: notebase | 基础路径: `/projects/notebase`

## 本地安装与启动

### 环境要求

- Python 3.12+
- conda 环境 `codingagent`（或任一含依赖的虚拟环境）

### 安装

```bash
# 进入项目目录
cd /Users/cqw/外部需求/proj-bd3aaa

# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板（首次运行）
cp .env.example .env
```

### 启动

```bash
# 开发模式（热重载）
uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload

# 生产模式
uvicorn backend.app:app --host 127.0.0.1 --port 19010
```

### 初始化演示数据

```bash
python -m backend.seed
```

这将创建演示账号 alice (demo123) 和 bob (demo123)，以及示例笔记和标签。

### 访问

- SPA 入口: `http://127.0.0.1:8000/projects/notebase/`
- API 文档 (Swagger): `http://127.0.0.1:8000/projects/notebase/docs`
- 健康检查: `http://127.0.0.1:8000/projects/notebase/health`

## 测试、构建与健康检查

### 运行自动测试

```bash
cd /Users/cqw/外部需求/proj-bd3aaa

# 运行全部测试
pytest tests/ -v --tb=short

# 运行特定模块
pytest tests/test_auth.py -v --tb=short
pytest tests/test_notes.py -v --tb=short
pytest tests/test_tags.py -v --tb=short
pytest tests/test_share.py -v --tb=short

# 带覆盖率报告
pytest tests/ -v --tb=short --cov=backend --cov-report=term
```

全部 36 项测试，覆盖：
- 认证: 注册/登录/登出/权限拦截 (9 项)
- 笔记: CRUD + 全文搜索 + 标签筛选 + 权限隔离 (8 项)
- 标签: CRUD + 笔记关联 + 用户隔离 (6 项)
- 分享: 链接生成/列出/公开访问/撤销/权限校验 (9 项)
- 基础设施: Cache-Control 响应头验证 (1 项，含在 test_auth 中)

### 健康检查

```bash
curl http://127.0.0.1:8000/projects/notebase/health
# → {"ok":true,"version":"0.0.1"}
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | `change-me-to-random-string` | Session Cookie 签名密钥，生产环境必须替换 |
| `DATABASE_URL` | `sqlite+aiosqlite:///./notebase.db` | 数据库连接 URL |
| `BASE_PATH` | `/projects/notebase` | 应用基础路径前缀 |
| `VERSION` | `0.0.1` | 当前版本号，用于静态资源版本令牌 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `SESSION_MAX_AGE` | `86400` | Session 过期时间（秒），默认 24 小时 |
| `DEMO_USER1` | `alice` | 演示账号 1（seed.py 使用） |
| `DEMO_PASS1` | `demo123` | 演示密码 1 |
| `DEMO_USER2` | `bob` | 演示账号 2（seed.py 使用） |
| `DEMO_PASS2` | `demo123` | 演示密码 2 |

## Base Path

项目必须支持 `/projects/notebase/` 前缀，静态资源和前端路由不得假设部署在 `/`。

**后端实现**：
- `backend/config.py`: `BASE_PATH = "/projects/notebase"`（可通过 `.env` 覆盖）
- 所有路由挂载在 `settings.BASE_PATH` 前缀下
- Cookie `path` 属性设为 `settings.BASE_PATH`

**前端实现**：
- `index.html` 由 Jinja2 模板注入 `window.__BASE_PATH__` 和 `window.__VERSION__`
- `api.js` 中所有请求 URL 基于 `window.__BASE_PATH__` 拼接
- SPA Hash 路由 (`#/login`, `#/notes`, `#/notes/{id}`) 不受 base path 影响

**公网浏览器验收时**，最终 URL 必须保留此前缀。

## 缓存策略

Hermes 验收要求：功能迭代后公网 URL 不变，必须防止老板浏览器命中缓存旧页面。

| 资源类型 | 策略 | 实现 |
|----------|------|------|
| HTML 文档 | `Cache-Control: no-cache` 真实 HTTP 响应头 | `CacheControlMiddleware` 对所有 `text/html` 响应注入 |
| API JSON | `Cache-Control: no-store` | `CacheControlMiddleware` 对所有 `application/json` 响应注入 |
| 静态资源 (CSS/JS) | URL 版本令牌 `?v=0.0.1` | Jinja2 模板渲染 `<link>`/`<script>` 时拼接 `version` 变量 |

**关键约束**：HTML 响应头必须由服务器框架层面下发，**不能使用 `<meta http-equiv>` 标签代替**。浏览器基本忽略 `<meta>` 的缓存语义。

## Aliyun systemd 与 Nginx

### systemd (notebase.service)

```ini
[Unit]
Description=notebase FastAPI application
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/notebase
EnvironmentFile=/opt/notebase/.env
ExecStart=/opt/notebase/venv/bin/uvicorn backend.app:app --host 127.0.0.1 --port 19010
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Nginx 配置

```nginx
location /projects/notebase/ {
    proxy_pass http://127.0.0.1:19010;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 部署命令

```bash
sudo systemctl daemon-reload
sudo systemctl enable notebase
sudo systemctl start notebase
sudo systemctl status notebase
```

## 日志查看

### 应用日志

```bash
# 开发模式: uvicorn 输出到 stdout
# 生产模式: systemd journal
journalctl -u notebase -f       # 实时跟踪
journalctl -u notebase --since "10 minutes ago"
journalctl -u notebase -n 50    # 最近 50 行
```

### 访问日志

Nginx access log 位于 `/var/log/nginx/access.log`。

## 常见故障与恢复

| 症状 | 可能原因 | 解决 |
|------|----------|------|
| `no such table: users` | 数据文件未初始化 | 重启 uvicorn（自动建表）；或运行 `python -m backend.seed` 初始化演示数据 |
| `database is locked` | SQLite 并发写入冲突 | SQLite 的 WAL 模式已启用；高并发场景建议迁移到 PostgreSQL |
| Cookie 未设置 | BASE_PATH 或域名不匹配 | 确认访问 URL 前缀与 `BASE_PATH` 一致；确认浏览器未禁用 Cookie |
| 静态资源 404 | 路径前缀缺失 | 确认 `frontend/` 目录存在；确认资源 URL 带 `/projects/notebase/static/` 前缀 |
| 页面白屏 | JS 模块加载失败 | 检查浏览器控制台错误；确认 marked.js CDN 可访问 |
| 缓存旧版本 | 浏览器缓存 HTML | 服务器应下发 `Cache-Control: no-cache` 响应头；确认中间件已注册 |
| `pip install` 失败 (bcrypt) | 系统缺少编译依赖 | macOS: `brew install libffi`; Linux: `apt install build-essential libffi-dev` |

## 回滚到精确 Tag

```bash
cd /opt/notebase
git fetch --tags
git checkout tags/0.0.1
sudo systemctl restart notebase
```
