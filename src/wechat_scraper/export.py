from __future__ import annotations

import json
import re
from pathlib import Path

from .article import Article


def sanitize_filename(name: str, *, max_length: int = 80) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "_", name.strip())
    cleaned = cleaned.strip("._")
    if not cleaned:
        cleaned = "untitled"
    return cleaned[:max_length]


def export_article(article: Article, output_dir: Path, *, fmt: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = sanitize_filename(article.title)

    if fmt == "json":
        path = output_dir / f"{stem}.json"
        path.write_text(
            json.dumps(article.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    if fmt == "html":
        path = output_dir / f"{stem}.html"
        path.write_text(render_html_document(article), encoding="utf-8")
        return path

    if fmt == "md":
        path = output_dir / f"{stem}.md"
        path.write_text(render_markdown(article), encoding="utf-8")
        return path

    if fmt == "txt":
        path = output_dir / f"{stem}.txt"
        path.write_text(render_plain_text(article), encoding="utf-8")
        return path

    raise ValueError(f"Unsupported format: {fmt}")


def render_markdown(article: Article) -> str:
    meta = [
        f"# {article.title}",
        "",
        f"- **公众号**: {article.account_name}",
        f"- **作者**: {article.author}",
        f"- **发布时间**: {article.published_at}",
        f"- **链接**: {article.url}",
    ]
    if article.summary:
        meta.append(f"- **摘要**: {article.summary}")
    meta.extend(["", article.content_text, ""])
    return "\n".join(meta)


def render_plain_text(article: Article) -> str:
    header = [
        article.title,
        f"公众号: {article.account_name}",
        f"作者: {article.author}",
        f"发布时间: {article.published_at}",
        f"链接: {article.url}",
        "",
    ]
    return "\n".join(header + [article.content_text, ""])


def render_html_document(article: Article) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{article.title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.7; max-width: 860px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
    .meta {{ color: #666; font-size: 14px; margin-bottom: 1.5rem; }}
    img {{ max-width: 100%; height: auto; }}
  </style>
</head>
<body>
  <h1>{article.title}</h1>
  <div class="meta">
    <div>公众号：{article.account_name}</div>
    <div>作者：{article.author}</div>
    <div>发布时间：{article.published_at}</div>
    <div>原文：<a href="{article.url}">{article.url}</a></div>
  </div>
  <article>{article.content_html}</article>
</body>
</html>
"""
