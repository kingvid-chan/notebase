"""Markdown → HTML 渲染 + bleach XSS 清洗。"""

import bleach
import markdown


class MarkdownRenderer:
    """服务端 Markdown 渲染器：Python-Markdown + bleach 白名单过滤。

    bleach 白名单只允许安全的 HTML 标签和属性，禁止 <script>、<style>
    和 on* 事件属性，防止 XSS 攻击。
    """

    ALLOWED_TAGS = [
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "a", "img", "ul", "ol", "li",
        "code", "pre", "blockquote",
        "em", "strong", "table", "thead", "tbody",
        "tr", "th", "td", "hr", "br",
        "span", "div",
        "del", "ins", "sub", "sup",
        "input",  # 用于 checkbox ([[ ], [x]])
    ]
    ALLOWED_ATTRS = {
        "a": ["href", "title"],
        "img": ["src", "alt", "title"],
        "input": ["type", "checked", "disabled"],
        "*": ["class"],
    }
    MARKDOWN_EXTENSIONS = [
        "fenced_code",
        "tables",
        "codehilite",
        "nl2br",
        "sane_lists",
    ]

    def render(self, md_text: str) -> str:
        """将 Markdown 文本渲染为安全 HTML。"""
        html = markdown.markdown(
            md_text, extensions=self.MARKDOWN_EXTENSIONS
        )
        return bleach.clean(
            html,
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRS,
            strip=True,
        )
