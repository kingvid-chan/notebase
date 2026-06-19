"""演示数据初始化脚本。
运行方式：python -m backend.seed
"""

import asyncio

from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import Base, async_session, engine
from backend.models import Note, NoteTag, ShareLink, Tag, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEMO_NOTES = [
    {
        "title": "欢迎使用 Notebase",
        "content_markdown": (
            "# 欢迎使用 Notebase 🎉\n\n"
            "这是一个**简单、快速**的笔记管理系统。\n\n"
            "## 功能特性\n\n"
            "- 📝 Markdown 笔记编辑\n"
            "- 🏷️ 标签分类管理\n"
            "- 🔍 全文搜索\n"
            "- 🔗 公开分享链接\n\n"
            "## 快捷操作\n\n"
            "1. 点击「新建笔记」开始写作\n"
            "2. 使用 `#` 创建标题\n"
            "3. 用 `**粗体**` 和 `*斜体*` 排版\n"
            "4. 点击分享按钮生成公开链接\n\n"
            "> 提示：左侧编辑，右侧实时预览！"
        ),
        "tags": ["入门", "帮助"],
    },
    {
        "title": "Python 学习笔记",
        "content_markdown": (
            "# Python 学习笔记\n\n"
            "## 列表推导式\n\n"
            "```python\n"
            "squares = [x**2 for x in range(10)]\n"
            "# [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]\n"
            "```\n\n"
            "## 字典操作\n\n"
            "```python\n"
            "user = {\"name\": \"Alice\", \"age\": 30}\n"
            "user.get(\"email\", \"未知\")\n"
            "```\n\n"
            "## 常用库\n\n"
            "| 库 | 用途 |\n"
            "|----|------|\n"
            "| FastAPI | Web 框架 |\n"
            "| SQLAlchemy | ORM |\n"
            "| pytest | 测试 |"
        ),
        "tags": ["Python", "编程"],
    },
    {
        "title": "项目架构设计思路",
        "content_markdown": (
            "# 项目架构设计思路\n\n"
            "## 分层架构\n\n"
            "```\n"
            "前端 SPA (Vanilla JS)\n"
            "  ├── Hash Router\n"
            "  ├── API Client (Fetch)\n"
            "  └── Components\n"
            "后端 API (FastAPI)\n"
            "  ├── Routers (HTTP 层)\n"
            "  ├── Services (业务逻辑)\n"
            "  ├── Models (ORM)\n"
            "  └── Middleware\n"
            "数据库 (SQLite)\n"
            "```\n\n"
            "## 设计原则\n\n"
            "- **简单优先**：0.0.1 用最简单的方案\n"
            "- **安全第一**：XSS 防护、密码哈希、权限隔离\n"
            "- **零依赖前端**：不引入构建工具"
        ),
        "tags": ["架构", "设计"],
    },
    {
        "title": "待办事项",
        "content_markdown": (
            "# 待办事项\n\n"
            "- [x] 完成技术方案\n"
            "- [x] 搭建项目骨架\n"
            "- [ ] 实现认证模块\n"
            "- [ ] 实现笔记 CRUD\n"
            "- [ ] 编写前端 SPA\n"
            "- [ ] 编写测试用例\n"
            "- [ ] 部署上线\n\n"
            "## 优先级\n\n"
            "1. 🔴 P0: 核心 CRUD\n"
            "2. 🟡 P1: 搜索和标签\n"
            "3. 🟢 P2: 分享功能"
        ),
        "tags": ["个人"],
    },
    {
        "title": "Markdown 语法速查",
        "content_markdown": (
            "# Markdown 语法速查\n\n"
            "## 标题\n\n"
            "`# H1` `## H2` `### H3`\n\n"
            "## 排版\n\n"
            "- **粗体**：`**text**`\n"
            "- *斜体*：`*text*`\n"
            "- ~~删除线~~：`~~text~~`\n"
            "- `代码`：`` `code` ``\n\n"
            "## 链接和图片\n\n"
            "[链接文本](url)\n"
            "![图片描述](url)\n\n"
            "## 代码块\n\n"
            "```python\nprint('hello')\n```\n\n"
            "## 引用\n\n"
            "> 这是一段引用文字\n\n"
            "## 表格\n\n"
            "| 列A | 列B |\n"
            "|-----|-----|\n"
            "| a1  | b1  |"
        ),
        "tags": ["帮助", "参考"],
    },
]


async def _create_fts5(conn):
    """创建 FTS5 虚拟表用于全文搜索。"""
    await conn.execute(text("DROP TABLE IF EXISTS notes_fts"))
    # content 表模式：FTS5 索引的数据来自外部 content 表（notes）
    await conn.execute(
        text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5("
            "    title,"
            "    content_markdown,"
            "    content='notes',"
            "    content_rowid='id'"
            ")"
        )
    )
    # 触发器：insert / delete / update 时自动同步 FTS 索引
    await conn.execute(
        text(
            "CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN "
            "  INSERT INTO notes_fts(rowid, title, content_markdown) "
            "  VALUES (new.id, new.title, new.content_markdown); "
            "END"
        )
    )
    await conn.execute(
        text(
            "CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN "
            "  INSERT INTO notes_fts(notes_fts, rowid, title, content_markdown) "
            "  VALUES ('delete', old.id, old.title, old.content_markdown); "
            "END"
        )
    )
    await conn.execute(
        text(
            "CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN "
            "  INSERT INTO notes_fts(notes_fts, rowid, title, content_markdown) "
            "  VALUES ('delete', old.id, old.title, old.content_markdown); "
            "  INSERT INTO notes_fts(rowid, title, content_markdown) "
            "  VALUES (new.id, new.title, new.content_markdown); "
            "END"
        )
    )


async def _insert_demo_user(
    session: AsyncSession, username: str, password: str, email: str
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=pwd_context.hash(password),
    )
    session.add(user)
    return user


async def _insert_demo_note(
    session: AsyncSession,
    user: User,
    title: str,
    content_markdown: str,
    tags: list[str],
    markdown_renderer,
) -> Note:
    content_html = markdown_renderer.render(content_markdown)
    note = Note(
        user_id=user.id,
        title=title,
        content_markdown=content_markdown,
        content_html=content_html,
    )
    session.add(note)
    await session.flush()

    for tag_name in tags:
        tag = Tag(name=tag_name, user_id=user.id)
        session.add(tag)
        await session.flush()
        session.add(NoteTag(note_id=note.id, tag_id=tag.id))

    return note


async def seed():
    """主入口：创建表 + 种子数据。"""
    import markdown
    import bleach

    ALLOWED_TAGS = [
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "a", "img", "ul", "ol", "li",
        "code", "pre", "blockquote",
        "em", "strong", "table", "thead", "tbody",
        "tr", "th", "td", "hr", "br",
        "span", "div",
    ]
    ALLOWED_ATTRS = {"a": ["href", "title"], "img": ["src", "alt", "title"], "*": ["class"]}

    def _render(md_text: str) -> str:
        html = markdown.markdown(md_text, extensions=["fenced_code", "tables", "codehilite"])
        return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)

    class _Renderer:
        render = staticmethod(_render)

    renderer = _Renderer()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _create_fts5(conn)

    async with async_session() as session:
        # 演示用户
        alice = await _insert_demo_user(
            session, settings.DEMO_USER1, settings.DEMO_PASS1, "alice@example.com"
        )
        bob = await _insert_demo_user(
            session, settings.DEMO_USER2, settings.DEMO_PASS2, "bob@example.com"
        )
        await session.flush()

        # Alice 的演示笔记
        for note_data in DEMO_NOTES:
            await _insert_demo_note(
                session,
                alice,
                note_data["title"],
                note_data["content_markdown"],
                note_data["tags"],
                renderer,
            )

        # Bob 的一条笔记
        note = Note(
            user_id=bob.id,
            title="Bob 的私密笔记",
            content_markdown="这是我的私密笔记，只有我能看到。",
            content_html=renderer.render("这是我的私密笔记，只有我能看到。"),
        )
        session.add(note)
        await session.flush()

        tag = Tag(name="私密", user_id=bob.id)
        session.add(tag)
        await session.flush()
        session.add(NoteTag(note_id=note.id, tag_id=tag.id))

        # 创建一个公开分享链接（Alice 的第一条笔记）
        import secrets

        first_note = (
            await session.execute(
                text("SELECT id FROM notes WHERE user_id = :uid ORDER BY id LIMIT 1"),
                {"uid": alice.id},
            )
        ).scalar_one()

        share = ShareLink(
            note_id=first_note,
            token=secrets.token_urlsafe(32),
        )
        session.add(share)

        await session.commit()

    print(f"✅ 种子数据已就绪。演示用户：{settings.DEMO_USER1} / {settings.DEMO_PASS1}")


if __name__ == "__main__":
    asyncio.run(seed())
