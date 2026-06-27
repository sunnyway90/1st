from __future__ import annotations

import unittest

from wechat_scraper.article import parse_article_html
from wechat_scraper.export import render_markdown, sanitize_filename


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

    def test_sanitize_filename(self) -> None:
        self.assertEqual(sanitize_filename('a/b:c?d"'), "a_b_c_d")


if __name__ == "__main__":
    unittest.main()
