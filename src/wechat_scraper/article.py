from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


@dataclass(frozen=True)
class Article:
    url: str
    title: str
    account_name: str
    author: str
    published_at: str
    summary: str
    content_html: str
    content_text: str
    biz: str
    mid: str
    idx: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "account_name": self.account_name,
            "author": self.author,
            "published_at": self.published_at,
            "summary": self.summary,
            "content_html": self.content_html,
            "content_text": self.content_text,
            "biz": self.biz,
            "mid": self.mid,
            "idx": self.idx,
        }


class ArticleFetchError(RuntimeError):
    pass


def fetch_article(url: str, *, timeout: float = 30.0, retries: int = 2) -> Article:
    normalized = _normalize_article_url(url)
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            response = requests.get(
                normalized,
                headers={**DEFAULT_HEADERS, "Referer": "https://mp.weixin.qq.com/"},
                timeout=timeout,
            )
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            return parse_article_html(normalized, response.text)
        except Exception as exc:  # noqa: BLE001 - retry wrapper
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))

    raise ArticleFetchError(f"Failed to fetch article: {last_error}") from last_error


def parse_article_html(url: str, page_html: str) -> Article:
    if _looks_like_verification_page(page_html):
        raise ArticleFetchError(
            "WeChat returned a verification page. Open the link in a browser first, "
            "or retry later with a residential network."
        )

    soup = BeautifulSoup(page_html, "html.parser")
    title = _first_non_empty(
        _meta_content(soup, "og:title"),
        _script_var(page_html, "msg_title"),
        _text(soup.select_one("#activity-name")),
    )
    account_name = _first_non_empty(
        _text(soup.select_one("#js_name")),
        _script_var(page_html, "nickname"),
    )
    author = _first_non_empty(
        _text(soup.select_one("#js_author_name")),
        _script_var(page_html, "author"),
        account_name,
    )
    summary = _first_non_empty(
        _meta_content(soup, "og:description"),
        _script_var(page_html, "msg_desc"),
    )

    content_node = soup.select_one("#js_content")
    if content_node is None:
        raise ArticleFetchError("Article body (#js_content) not found in page HTML.")

    content_html = _normalize_content_html(content_node, base_url=url)
    content_text = _html_to_text(content_html)
    published_at = _extract_publish_time(page_html, soup)
    biz, mid, idx = _extract_ids(page_html, url)

    if not title:
        raise ArticleFetchError("Could not parse article title.")

    return Article(
        url=url,
        title=title,
        account_name=account_name,
        author=author,
        published_at=published_at,
        summary=summary,
        content_html=content_html,
        content_text=content_text,
        biz=biz,
        mid=mid,
        idx=idx,
    )


def _normalize_article_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.netloc not in {"mp.weixin.qq.com", "www.mp.weixin.qq.com"}:
        raise ValueError("URL must be a WeChat article link (mp.weixin.qq.com/s/...).")
    return url.strip()


def _looks_like_verification_page(page_html: str) -> bool:
    markers = (
        "环境异常",
        "完成验证后即可继续访问",
        "secitptpage",
        "verify.weixin.qq.com",
    )
    return any(marker in page_html for marker in markers)


def _meta_content(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", property=name) or soup.find("meta", attrs={"name": name})
    return _clean_text(tag.get("content", "")) if tag else ""


def _script_var(page_html: str, name: str) -> str:
    patterns = [
        rf"var\s+{name}\s*=\s*'([^']*)'",
        rf'var\s+{name}\s*=\s*"([^"]*)"',
        rf"window\.{name}\s*=\s*'([^']*)'",
    ]
    for pattern in patterns:
        match = re.search(pattern, page_html)
        if match:
            return _clean_text(html.unescape(match.group(1)))
    return ""


def _text(node: Tag | None) -> str:
    return _clean_text(node.get_text(" ", strip=True)) if node else ""


def _clean_text(value: str) -> str:
    return html.unescape(value).replace("\xa0", " ").strip()


def _first_non_empty(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


def _extract_publish_time(page_html: str, soup: BeautifulSoup) -> str:
    publish_node = soup.select_one("#publish_time")
    if publish_node:
        return _text(publish_node)

    for key in ("ct", "createTime", "svr_time"):
        raw = _script_var(page_html, key)
        if raw.isdigit():
            timestamp = int(raw)
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
    return ""


def _extract_ids(page_html: str, url: str) -> tuple[str, str, str]:
    biz = _script_var(page_html, "biz") or _query_param(url, "__biz")
    mid = _script_var(page_html, "mid") or _query_param(url, "mid")
    idx = _script_var(page_html, "idx") or _query_param(url, "idx")
    return biz, mid, idx


def _query_param(url: str, key: str) -> str:
    match = re.search(rf"[?&]{re.escape(key)}=([^&]+)", url)
    return match.group(1) if match else ""


def _normalize_content_html(content_node: Tag, *, base_url: str) -> str:
    cloned = BeautifulSoup(str(content_node), "html.parser")
    root = cloned.select_one("#js_content") or cloned

    for tag in root.find_all(True):
        if not isinstance(tag, Tag):
            continue
        for attr in ("data-src", "data-original", "data-backsrc"):
            if tag.has_attr(attr) and attr.startswith("data-"):
                src = tag.get(attr)
                if src and not tag.get("src"):
                    tag["src"] = urljoin(base_url, src)
        style = tag.get("style")
        if isinstance(style, str):
            tag["style"] = re.sub(r"visibility\s*:\s*hidden;?", "", style)

    return "".join(str(child) for child in root.contents)


def _html_to_text(content_html: str) -> str:
    soup = BeautifulSoup(content_html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with(NavigableString("\n"))
    for block in soup.find_all(["p", "section", "div", "li", "h1", "h2", "h3", "h4"]):
        if block.get_text(strip=True):
            block.append(NavigableString("\n"))
    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
