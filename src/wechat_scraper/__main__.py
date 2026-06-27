from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .article import ArticleFetchError, fetch_article
from .export import export_article
from .mp_client import MpClient, MpCredentials


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wechat_scraper",
        description="Fetch WeChat public account articles (single URL or MP backend bulk mode).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch one article by URL.")
    fetch_parser.add_argument("url", help="WeChat article URL, e.g. https://mp.weixin.qq.com/s/...")
    fetch_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file path. If omitted, writes to --output-dir using article title.",
    )
    fetch_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/wechat"),
        help="Directory for exported files (default: output/wechat).",
    )
    fetch_parser.add_argument(
        "--format",
        choices=("md", "html", "json", "txt"),
        default="md",
        help="Export format (default: md).",
    )
    fetch_parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print parsed metadata and text to stdout as JSON.",
    )

    search_parser = subparsers.add_parser(
        "search",
        help="Search accounts via mp.weixin.qq.com backend (requires cookie/token).",
    )
    search_parser.add_argument("keyword", help="Account name keyword.")
    _add_mp_auth_args(search_parser)

    list_parser = subparsers.add_parser(
        "list",
        help="List recent articles for an account fakeid (requires cookie/token).",
    )
    list_parser.add_argument("--fakeid", required=True, help="Account fakeid from search results.")
    list_parser.add_argument("--begin", type=int, default=0)
    list_parser.add_argument("--count", type=int, default=10)
    _add_mp_auth_args(list_parser)

    download_parser = subparsers.add_parser(
        "download",
        help="Download recent articles for an account fakeid (requires cookie/token).",
    )
    download_parser.add_argument("--fakeid", required=True, help="Account fakeid from search results.")
    download_parser.add_argument("--limit", type=int, default=10, help="Max articles to download.")
    download_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/wechat"),
        help="Directory for exported files.",
    )
    download_parser.add_argument(
        "--format",
        choices=("md", "html", "json", "txt"),
        default="md",
        help="Export format (default: md).",
    )
    download_parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay between requests in seconds (default: 1.5).",
    )
    _add_mp_auth_args(download_parser)

    return parser


def _add_mp_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cookie", help="Cookie from mp.weixin.qq.com (or WECHAT_MP_COOKIE).")
    parser.add_argument("--token", help="token query param from mp.weixin.qq.com (or WECHAT_MP_TOKEN).")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "fetch":
            return _cmd_fetch(args)
        if args.command == "search":
            return _cmd_search(args)
        if args.command == "list":
            return _cmd_list(args)
        if args.command == "download":
            return _cmd_download(args)
    except (ArticleFetchError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


def _cmd_fetch(args: argparse.Namespace) -> int:
    article = fetch_article(args.url)
    if args.print_json:
        print(json.dumps(article.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.format == "json":
            args.output.write_text(
                json.dumps(article.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            from .export import render_html_document, render_markdown, render_plain_text

            renderers = {
                "md": render_markdown,
                "html": render_html_document,
                "txt": render_plain_text,
            }
            args.output.write_text(renderers[args.format](article), encoding="utf-8")
        print(args.output)
        return 0

    path = export_article(article, args.output_dir, fmt=args.format)
    print(path)
    return 0


def _credentials(args: argparse.Namespace) -> MpCredentials:
    cookie = (args.cookie or "").strip()
    token = (args.token or "").strip()
    if cookie and token:
        return MpCredentials(cookie=cookie, token=token)
    return MpCredentials.from_env()


def _cmd_search(args: argparse.Namespace) -> int:
    client = MpClient(_credentials(args))
    accounts = client.search_accounts(args.keyword)
    print(json.dumps([item.to_dict() for item in accounts], ensure_ascii=False, indent=2))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    client = MpClient(_credentials(args))
    articles = client.list_articles(args.fakeid, begin=args.begin, count=args.count)
    print(json.dumps([item.to_dict() for item in articles], ensure_ascii=False, indent=2))
    return 0


def _cmd_download(args: argparse.Namespace) -> int:
    client = MpClient(_credentials(args))
    articles = client.download_articles(
        args.fakeid,
        max_articles=args.limit,
        delay_seconds=args.delay,
    )
    paths = [export_article(article, args.output_dir, fmt=args.format) for article in articles]
    print(json.dumps([str(path) for path in paths], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
