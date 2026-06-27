from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from wechat_scraper.article import Article, parse_article_html
from wechat_scraper.assets import html_body_to_markdown
from wechat_scraper.export import render_markdown, sanitize_filename
from wechat_scraper.mp_client import AccountInfo, MpClient, MpCredentials
from wechat_scraper.pdf import combine_html_documents


SAMPLE_HTML = """
<html>
<head>
  <meta property="og:title" content="示例标题" />
  <meta property="og:description" content="示例摘要" />
</head>
<body>
  <h1 id="activity-name">示例标题</h1>
  <a id="js_name">测试公众号</a>
  <em id="publish_time">2026-03-09</em>
  <div id="js_content">
    <p>第一段文字</p>
    <p>第二段文字</p>
  </div>
  <script>
    var biz = "MzAwMDAwMDAwMA==";
    var mid = "2651000834";
    var idx = "1";
    var author = "tester";
  </script>
</body>
</html>
"""


class ArticleParserTests(unittest.TestCase):
    def test_parse_article_html(self) -> None:
        article = parse_article_html(
            "https://mp.weixin.qq.com/s/example",
            SAMPLE_HTML,
        )
        self.assertEqual(article.title, "示例标题")
        self.assertEqual(article.account_name, "测试公众号")
        self.assertEqual(article.author, "tester")
        self.assertEqual(article.summary, "示例摘要")
        self.assertIn("第一段文字", article.content_text)
        self.assertEqual(article.biz, "MzAwMDAwMDAwMA==")

    def test_render_markdown_contains_metadata(self) -> None:
        article = parse_article_html(
            "https://mp.weixin.qq.com/s/example",
            SAMPLE_HTML,
        )
        rendered = render_markdown(article)
        self.assertIn("# 示例标题", rendered)
        self.assertIn("测试公众号", rendered)
        self.assertIn("第一段文字", rendered)

    def test_render_markdown_with_localized_images(self) -> None:
        article = Article(
            url="https://mp.weixin.qq.com/s/example",
            title="图测试",
            account_name="测试公众号",
            author="tester",
            published_at="2026-03-09",
            summary="",
            content_html='<p>文字</p><img src="demo_assets/img_001.jpg" alt="demo" />',
            content_text="文字",
            biz="",
            mid="",
            idx="",
        )
        rendered = render_markdown(article, localized_images=True)
        self.assertIn("![demo](demo_assets/img_001.jpg)", rendered)

    def test_html_body_to_markdown(self) -> None:
        rendered = html_body_to_markdown('<p>你好</p><img src="a.jpg" alt="图" />')
        self.assertIn("你好", rendered)
        self.assertIn("![图](a.jpg)", rendered)

    def test_sanitize_filename(self) -> None:
        self.assertEqual(sanitize_filename('a/b:c?d"'), "a_b_c_d")

    def test_combine_html_documents_extracts_body(self) -> None:
        with self.subTest("combine"):
            temp_dir = Path("/tmp/wechat_scraper_test")
            temp_dir.mkdir(parents=True, exist_ok=True)
            first = temp_dir / "a.html"
            second = temp_dir / "b.html"
            first.write_text("<html><body><article><h1>A</h1></article></body></html>", encoding="utf-8")
            second.write_text("<html><body><article><h1>B</h1></article></body></html>", encoding="utf-8")
            combined = temp_dir / "combined.html"
            combine_html_documents([first, second], combined)
            text = combined.read_text(encoding="utf-8")
            self.assertIn("<h1>A</h1>", text)
            self.assertIn("<h1>B</h1>", text)
            self.assertNotIn("<html><body><article><h1>A</h1></article></body></html>", text)


class MpClientTests(unittest.TestCase):
    def test_find_account_prefers_exact_match(self) -> None:
        client = MpClient(MpCredentials(cookie="x", token="y"))
        accounts = [
            AccountInfo("1", "人民日报评论", "", "", ""),
            AccountInfo("2", "人民日报", "", "", ""),
        ]
        with patch.object(client, "search_accounts", return_value=accounts):
            account = client.find_account("人民日报")
        self.assertEqual(account.fakeid, "2")


if __name__ == "__main__":
    unittest.main()
