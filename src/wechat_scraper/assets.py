from __future__ import annotations

import hashlib
import mimetypes
import re
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from .article import DEFAULT_HEADERS, Article

IMAGE_SRC_ATTRS = ("src", "data-src", "data-original", "data-backsrc")


def localize_article_images(
    article: Article,
    asset_dir: Path,
    *,
    referer: str | None = None,
    timeout: float = 30.0,
) -> Article:
    asset_dir.mkdir(parents=True, exist_ok=True)
    soup = BeautifulSoup(article.content_html, "html.parser")
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    if referer:
        session.headers["Referer"] = referer

    for index, img in enumerate(soup.find_all("img"), start=1):
        image_url = _first_image_url(img)
        if not image_url:
            continue
        try:
            local_name = _download_image(session, image_url, asset_dir, index=index, timeout=timeout)
        except requests.RequestException:
            continue
        relative_path = f"{asset_dir.name}/{local_name}"
        img["src"] = relative_path
        for attr in ("data-src", "data-original", "data-backsrc"):
            if img.has_attr(attr):
                del img[attr]

    localized_html = "".join(str(child) for child in soup.contents)
    localized_text = _html_with_images_to_text(localized_html)
    return replace(
        article,
        content_html=localized_html,
        content_text=localized_text,
    )


def _first_image_url(img: Tag) -> str:
    for attr in IMAGE_SRC_ATTRS:
        value = img.get(attr)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _download_image(
    session: requests.Session,
    image_url: str,
    asset_dir: Path,
    *,
    index: int,
    timeout: float,
) -> str:
    response = session.get(image_url, timeout=timeout)
    response.raise_for_status()
    suffix = _guess_suffix(image_url, response.headers.get("Content-Type", ""))
    digest = hashlib.sha1(image_url.encode("utf-8")).hexdigest()[:10]
    filename = f"img_{index:03d}_{digest}{suffix}"
    (asset_dir / filename).write_bytes(response.content)
    return filename


def _guess_suffix(url: str, content_type: str) -> str:
    path_suffix = Path(urlparse(url).path).suffix.lower()
    if path_suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}:
        return path_suffix
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
    return guessed or ".jpg"


def _html_with_images_to_text(content_html: str) -> str:
    soup = BeautifulSoup(content_html, "html.parser")
    lines: list[str] = []

    def walk(node: Tag | NavigableString) -> None:
        if isinstance(node, NavigableString):
            text = str(node).strip()
            if text:
                lines.append(text)
            return
        if not isinstance(node, Tag):
            return
        if node.name == "img":
            src = node.get("src", "")
            if src:
                lines.append(f"[image: {src}]")
            return
        if node.name == "br":
            lines.append("")
            return
        for child in node.children:
            walk(child)
        if node.name in {"p", "section", "div", "li", "h1", "h2", "h3", "h4"} and node.get_text(strip=True):
            lines.append("")

    for child in soup.children:
        walk(child)

    cleaned: list[str] = []
    for line in lines:
        line = line.strip()
        if not line and (not cleaned or cleaned[-1] == ""):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def html_body_to_markdown(content_html: str) -> str:
    soup = BeautifulSoup(content_html, "html.parser")
    parts: list[str] = []

    def walk(node: Tag | NavigableString) -> None:
        if isinstance(node, NavigableString):
            text = str(node).strip()
            if text:
                parts.append(text)
            return
        if not isinstance(node, Tag):
            return
        if node.name == "img":
            alt = node.get("alt", "image")
            src = node.get("src", "")
            if src:
                parts.append(f"![{alt}]({src})")
            return
        if node.name == "br":
            parts.append("\n")
            return
        if node.name in {"h1", "h2", "h3", "h4"}:
            level = int(node.name[1])
            text = node.get_text(" ", strip=True)
            if text:
                parts.append(f"\n{'#' * level} {text}\n")
            return
        for child in node.children:
            walk(child)
        if node.name in {"p", "section", "div", "li"} and node.get_text(strip=True):
            parts.append("\n")

    for child in soup.children:
        walk(child)

    text = "".join(parts)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
