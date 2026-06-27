from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests

from .article import Article, ArticleFetchError, fetch_article

MP_ORIGIN = "https://mp.weixin.qq.com"


@dataclass(frozen=True)
class MpCredentials:
    cookie: str
    token: str

    @classmethod
    def from_env(cls) -> "MpCredentials":
        import os

        cookie = os.environ.get("WECHAT_MP_COOKIE", "").strip()
        token = os.environ.get("WECHAT_MP_TOKEN", "").strip()
        if not cookie or not token:
            raise ValueError(
                "Set WECHAT_MP_COOKIE and WECHAT_MP_TOKEN, or pass --cookie/--token."
            )
        return cls(cookie=cookie, token=token)


@dataclass(frozen=True)
class AccountInfo:
    fakeid: str
    nickname: str
    alias: str
    signature: str
    round_head_img: str

    def to_dict(self) -> dict[str, str]:
        return {
            "fakeid": self.fakeid,
            "nickname": self.nickname,
            "alias": self.alias,
            "signature": self.signature,
            "round_head_img": self.round_head_img,
        }


@dataclass(frozen=True)
class ArticleSummary:
    title: str
    link: str
    digest: str
    author: str
    create_time: int
    update_time: int
    cover: str
    aid: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "link": self.link,
            "digest": self.digest,
            "author": self.author,
            "create_time": self.create_time,
            "update_time": self.update_time,
            "cover": self.cover,
            "aid": self.aid,
        }


class MpClient:
    """Client for the WeChat Official Account backend search/list APIs."""

    def __init__(self, credentials: MpCredentials, *, timeout: float = 30.0) -> None:
        self.credentials = credentials
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Cookie": credentials.cookie,
                "Referer": f"{MP_ORIGIN}/",
            }
        )

    def search_accounts(self, keyword: str, *, begin: int = 0, count: int = 5) -> list[AccountInfo]:
        params = {
            "action": "search_biz",
            "begin": begin,
            "count": count,
            "query": keyword,
            "token": self.credentials.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
        }
        payload = self._get_json("/cgi-bin/searchbiz", params)
        return [
            AccountInfo(
                fakeid=item.get("fakeid", ""),
                nickname=item.get("nickname", ""),
                alias=item.get("alias", ""),
                signature=item.get("signature", ""),
                round_head_img=item.get("round_head_img", ""),
            )
            for item in payload.get("list", [])
        ]

    def list_articles(
        self,
        fakeid: str,
        *,
        begin: int = 0,
        count: int = 5,
    ) -> list[ArticleSummary]:
        params = {
            "action": "list_ex",
            "begin": begin,
            "count": count,
            "fakeid": fakeid,
            "type": "9",
            "query": "",
            "token": self.credentials.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
        }
        payload = self._get_json("/cgi-bin/appmsgpublish", params)
        publish_page = payload.get("publish_page")
        appmsgex: list[dict[str, Any]] = []

        if isinstance(publish_page, str) and publish_page:
            try:
                publish_data = json.loads(publish_page)
                for publish_info in publish_data.get("publish_list", []):
                    publish_info_raw = publish_info.get("publish_info")
                    if not isinstance(publish_info_raw, str):
                        continue
                    info = json.loads(publish_info_raw)
                    appmsgex.extend(info.get("appmsgex", []))
            except json.JSONDecodeError:
                appmsgex = []

        if not appmsgex:
            legacy = self._get_json("/cgi-bin/appmsg", {**params, "action": "list_ex"})
            appmsgex = legacy.get("app_msg_list", []) or legacy.get("appmsg_list", [])

        return [self._to_article_summary(item) for item in appmsgex]

    def iter_articles(
        self,
        fakeid: str,
        *,
        max_articles: int | None = None,
        page_size: int = 5,
        delay_seconds: float = 1.0,
    ):
        begin = 0
        fetched = 0
        while True:
            batch = self.list_articles(fakeid, begin=begin, count=page_size)
            if not batch:
                break
            for item in batch:
                yield item
                fetched += 1
                if max_articles is not None and fetched >= max_articles:
                    return
            begin += page_size
            time.sleep(delay_seconds)

    def download_articles(
        self,
        fakeid: str,
        *,
        max_articles: int = 10,
        delay_seconds: float = 1.5,
    ) -> list[Article]:
        articles: list[Article] = []
        for summary in self.iter_articles(
            fakeid,
            max_articles=max_articles,
            delay_seconds=delay_seconds,
        ):
            if not summary.link:
                continue
            try:
                articles.append(fetch_article(summary.link))
            except ArticleFetchError:
                continue
            time.sleep(delay_seconds)
        return articles

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self.session.get(
            f"{MP_ORIGIN}{path}",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        base_resp = payload.get("base_resp", {})
        ret = base_resp.get("ret")
        if ret not in (0, "0", None):
            err_msg = base_resp.get("err_msg", "unknown error")
            raise RuntimeError(f"WeChat MP API error ret={ret}: {err_msg}")
        return payload

    @staticmethod
    def _to_article_summary(item: dict[str, Any]) -> ArticleSummary:
        link = item.get("link") or item.get("content_url") or ""
        if link.startswith("http://"):
            link = "https://" + link[len("http://") :]
        return ArticleSummary(
            title=item.get("title", ""),
            link=link,
            digest=item.get("digest", ""),
            author=item.get("author_name", "") or item.get("author", ""),
            create_time=int(item.get("create_time") or 0),
            update_time=int(item.get("update_time") or 0),
            cover=item.get("cover", "") or item.get("cover_url", ""),
            aid=str(item.get("aid", "")),
        )


def account_profile_url(nickname: str) -> str:
    return f"{MP_ORIGIN}/cgi-bin/searchbiz?action=search_biz&query={quote(nickname)}"
