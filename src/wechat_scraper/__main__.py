from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .article import ArticleFetchError, fetch_article
from .export import export_article, prepare_article_for_export, render_html_document, render_markdown, render_plain_text
from .mp_client import MpClient, MpCredentials
from .pdf import PdfConversionError, batch_html_to_pdf


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
        "--localize-images",
        action="store_true",
        help="Download images and rewrite HTML/Markdown to use local asset paths.",
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
        "--localize-images",
        action="store_true",
        help="Download images and rewrite exported files to use local asset paths.",
    )
    download_parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay between requests in seconds (default: 1.5).",
    )
    _add_mp_auth_args(download_parser)

    download_account_parser = subparsers.add_parser(
        "download-account",
        help="Search by account name and download recent articles in one step.",
    )
    download_account_parser.add_argument("keyword", help="Account nickname keyword.")
    download_account_parser.add_argument("--limit", type=int, default=10, help="Max articles to download.")
    download_account_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/wechat"),
        help="Directory for exported files.",
    )
    download_account_parser.add_argument(
        "--format",
        choices=("md", "html", "json", "txt"),
        default="md",
        help="Export format (default: md).",
    )
    download_account_parser.add_argument(
        "--localize-images",
        action="store_true",
        help="Download images and rewrite exported files to use local asset paths.",
    )
    download_account_parser.add_argument(
        "--exact",
        action="store_true",
        help="Require an exact nickname/alias match.",
    )
    download_account_parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay between requests in seconds (default: 1.5).",
    )
    _add_mp_auth_args(download_account_parser)

    pdf_parser = subparsers.add_parser(
        "html-to-pdf",
        help="Batch convert exported HTML files to PDF using headless Chrome.",
    )
    pdf_parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing .html files.",
    )
    pdf_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/wechat/pdf"),
        help="Directory for generated PDF files.",
    )
    pdf_parser.add_argument(
        "--group-size",
        type=int,
        default=1,
        help="Merge every N HTML files into one PDF volume (default: 1).",
    )
    pdf_parser.add_argument(
        "--merge-volumes",
        type=int,
        help="Merge every N generated PDFs into a larger merged PDF.",
    )

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
        if args.command == "download-account":
            return _cmd_download_account(args)
        if args.command == "html-to-pdf":
            return _cmd_html_to_pdf(args)
    except (ArticleFetchError, PdfConversionError, ValueError, RuntimeError) as exc:
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
        prepared = prepare_article_for_export(
            article,
            args.output.parent,
            localize_images=args.localize_images,
        )
        if args.format == "json":
            args.output.write_text(
                json.dumps(prepared.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        else:
            renderers = {
                "md": lambda item: render_markdown(item, localized_images=args.localize_images),
                "html": render_html_document,
                "txt": render_plain_text,
            }
            args.output.write_text(renderers[args.format](prepared), encoding="utf-8")
        print(args.output)
        return 0

    path = export_article(
        article,
        args.output_dir,
        fmt=args.format,
        localize_images=args.localize_images,
    )
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


def _export_articles(
    articles,
    output_dir: Path,
    *,
    fmt: str,
    localize_images: bool,
) -> list[Path]:
    return [
        export_article(article, output_dir, fmt=fmt, localize_images=localize_images)
        for article in articles
    ]


def _cmd_download(args: argparse.Namespace) -> int:
    client = MpClient(_credentials(args))
    articles = client.download_articles(
        args.fakeid,
        max_articles=args.limit,
        delay_seconds=args.delay,
    )
    paths = _export_articles(
        articles,
        args.output_dir,
        fmt=args.format,
        localize_images=args.localize_images,
    )
    print(json.dumps([str(path) for path in paths], ensure_ascii=False, indent=2))
    return 0


def _cmd_download_account(args: argparse.Namespace) -> int:
    client = MpClient(_credentials(args))
    account, articles = client.download_account(
        args.keyword,
        max_articles=args.limit,
        delay_seconds=args.delay,
        exact=args.exact,
    )
    account_dir = args.output_dir / sanitize_account_dir(account.nickname)
    paths = _export_articles(
        articles,
        account_dir,
        fmt=args.format,
        localize_images=args.localize_images,
    )
    payload = {
        "account": account.to_dict(),
        "output_dir": str(account_dir),
        "files": [str(path) for path in paths],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_html_to_pdf(args: argparse.Namespace) -> int:
    paths = batch_html_to_pdf(
        args.input_dir,
        args.output_dir,
        group_size=args.group_size,
        merge_volumes=args.merge_volumes,
    )
    print(json.dumps([str(path) for path in paths], ensure_ascii=False, indent=2))
    return 0


def sanitize_account_dir(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name.strip())
    return cleaned or "account"


if __name__ == "__main__":
    raise SystemExit(main())
