from __future__ import annotations

import json
import re
from pathlib import Path

from .article import Article
from .assets import html_body_to_markdown, localize_article_images


def sanitize_filename(name: str, *, max_length: int = 80) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\s]+', "_", name.strip())
    cleaned = cleaned.strip("._")
    if not cleaned:
        cleaned = "untitled"
    return cleaned[:max_length]


def prepare_article_for_export(
    article: Article,
    output_dir: Path,
    *,
    localize_images: bool = False,
) -> Article:
    if not localize_images:
        return article

    stem = sanitize_filename(article.title)
    asset_dir = output_dir / f"{stem}_assets"
    return localize_article_images(article, asset_dir, referer=article.url)


def export_article(
    article: Article,
    output_dir: Path,
    *,
    fmt: str,
    localize_images: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    prepared = prepare_article_for_export(article, output_dir, localize_images=localize_images)
    stem = sanitize_filename(prepared.title)

    if fmt == "json":
        path = output_dir / f"{stem}.json"
        path.write_text(
            json.dumps(prepared.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    if fmt == "html":
        path = output_dir / f"{stem}.html"
        path.write_text(render_html_document(prepared), encoding="utf-8")
        return path

    if fmt == "md":
        path = output_dir / f"{stem}.md"
        path.write_text(render_markdown(prepared, localized_images=localize_images), encoding="utf-8")
        return path

    if fmt == "txt":
        path = output_dir / f"{stem}.txt"
        path.write_text(render_plain_text(prepared), encoding="utf-8")
        return path

    raise ValueError(f"Unsupported format: {fmt}")


def render_markdown(article: Article, *, localized_images: bool = False) -> str:
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
    body = (
        html_body_to_markdown(article.content_html)
        if localized_images
        else article.content_text
    )
    meta.extend(["", body, ""])
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
