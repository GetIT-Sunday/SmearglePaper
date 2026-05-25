from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from smearglepaper.collector import parse_arxiv_feed, topic_queries
from smearglepaper.llm import chat_completions_base_url
from smearglepaper.models import PaperMeta
from smearglepaper.quality import review_article_file
from smearglepaper.ranker import rank_papers
from smearglepaper.renderer import WechatRenderer
from smearglepaper.workflow import append_figures


class CoreTests(unittest.TestCase):
    def test_parse_arxiv_feed(self) -> None:
        xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <id>http://arxiv.org/abs/2401.00001v1</id>
            <title> Test Paper </title>
            <summary> A useful abstract. </summary>
            <published>2026-05-20T00:00:00Z</published>
            <updated>2026-05-20T00:00:00Z</updated>
            <author><name>Ada Lovelace</name></author>
            <category term="cs.AI"/>
            <link title="pdf" href="http://arxiv.org/pdf/2401.00001v1"/>
          </entry>
        </feed>"""
        papers = parse_arxiv_feed(xml)
        self.assertEqual(papers[0].paper_id, "2401.00001v1")
        self.assertEqual(papers[0].authors, ["Ada Lovelace"])
        self.assertEqual(papers[0].pdf_url, "http://arxiv.org/pdf/2401.00001v1")

    def test_rank_papers_prefers_relevance(self) -> None:
        papers = [
            PaperMeta("a", "Graph Theory", [], "math", "arxiv", "", None, "2026-05-20T00:00:00Z", categories=["math.CO"]),
            PaperMeta("b", "Large Language Model Reasoning", [], "reasoning agent", "arxiv", "", None, "2026-05-20T00:00:00Z", categories=["cs.AI"]),
        ]
        rows = rank_papers(papers, query="large language model reasoning", top_k=1)
        self.assertEqual(rows[0]["paper"]["paper_id"], "b")

    def test_renderer_outputs_html(self) -> None:
        html = WechatRenderer().render("# 标题\n\n## 小节\n\n正文")
        self.assertIn("<html", html)
        self.assertIn("标题", html)

    def test_append_figures(self) -> None:
        markdown = append_figures("# Title", ["/tmp/a.png", "/tmp/b.png"])
        self.assertIn("论文图表候选", markdown)
        self.assertIn("](/tmp/a.png)", markdown)

    def test_nlp_topic_presets(self) -> None:
        queries = topic_queries("nlp_semantics_syntax_pragmatics")
        self.assertGreaterEqual(len(queries), 3)
        self.assertTrue(all("cat:cs.CL" in query for query in queries))

    def test_chat_completions_base_url(self) -> None:
        self.assertEqual(chat_completions_base_url("https://example.com"), "https://example.com/v1")
        self.assertEqual(chat_completions_base_url("https://example.com/v1"), "https://example.com/v1")

    def test_review_article_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "article.md"
            path.write_text("# 一个信息量足够的标题\n\n## 一句话结论\n正文\n", encoding="utf-8")
            report = review_article_file(path)
            self.assertIn("score", report)
            self.assertEqual(report["figure_count"], 0)


if __name__ == "__main__":
    unittest.main()
