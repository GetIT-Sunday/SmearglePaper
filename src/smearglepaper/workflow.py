from __future__ import annotations

import sys
from pathlib import Path

from .collector import ArxivCollector
from .config import DATA_DIR, runtime_settings
from .cover import create_cover
from .llm import ArticleWriter
from .models import Article, PaperMeta
from .ranker import rank_papers
from .reader import PaperReader
from .renderer import WechatRenderer
from .storage import read_json, slugify, write_json
from .wechat import WechatClient


class SmearglePaperWorkflow:
    def __init__(self) -> None:
        self.collector = ArxivCollector()
        self.reader = PaperReader()
        self.writer = ArticleWriter()
        self.renderer = WechatRenderer()

    def collect(self, topic: str | None, query: str | None, days: int, sources: list[str], max_results: int) -> list[dict[str, object]]:
        if sources != ["arxiv"] and any(source != "arxiv" for source in sources):
            raise ValueError("Only arxiv is currently implemented.")
        papers = self.collector.collect(topic, query, days, max_results)
        payload = [paper.to_dict() for paper in papers]
        write_json(DATA_DIR / "papers" / "latest.json", payload)
        return payload

    def load_papers_file(self, path: Path) -> list[PaperMeta]:
        return [PaperMeta.from_dict(item) for item in read_json(path, [])]

    def rank(self, papers: list[PaperMeta], top_k: int = 5, query: str | None = None) -> list[dict[str, object]]:
        rows = rank_papers(papers, query=query, top_k=top_k)
        write_json(DATA_DIR / "papers" / "ranked_latest.json", rows)
        return rows

    def read(self, paper: PaperMeta) -> dict[str, object]:
        return self.reader.read(paper)

    def write_article(self, paper: PaperMeta, parsed: dict[str, object] | None = None) -> dict[str, object]:
        markdown = self.writer.write(paper, parsed=parsed)
        figure_paths = [str(path) for path in (parsed or {}).get("figures", [])]
        if figure_paths:
            markdown = append_figures(markdown, figure_paths)
        html = self.renderer.render(markdown)
        digest = paper.abstract[:110] if paper.abstract else paper.title[:110]
        article = Article(
            paper=paper,
            title=_article_title(markdown, paper.title),
            digest=digest,
            markdown=markdown,
            html=html,
            cover_path=create_cover(paper.title, "AI Paper Close Reading"),
            figure_paths=figure_paths,
            word_count=len(markdown),
        )
        base = DATA_DIR / "articles" / slugify(paper.paper_id)
        write_json(base.with_suffix(".json"), article.to_dict())
        base.with_suffix(".md").write_text(markdown, encoding="utf-8")
        base.with_suffix(".html").write_text(html, encoding="utf-8")
        return {"paper_id": paper.paper_id, "article_json": str(base.with_suffix(".json")), "markdown": str(base.with_suffix(".md")), "html": str(base.with_suffix(".html")), "cover": article.cover_path, "word_count": article.word_count}

    def create_topic_draft(self, topic: str | None, query: str | None, paper_url: str | None, days: int, top_k: int, dry_run: bool) -> dict[str, object]:
        paper = self._resolve_paper(topic, query, paper_url, days, top_k)
        parsed = self.read(paper)
        parsed_payload = read_json(Path(parsed["parsed"]), {})
        article_paths = self.write_article(paper, parsed=parsed_payload)
        article = Article.from_dict(read_json(Path(article_paths["article_json"]), {}))
        report = WechatClient(dry_run=dry_run).create_draft(article)
        return {"paper": paper.to_dict(), "parsed": parsed, "article": article_paths, "draft": report}

    def auto_publish(self, topic: str | None, query: str | None, paper_url: str | None, days: int, top_k: int, create_draft: bool, auto_publish: bool, no_publish: bool) -> dict[str, object]:
        dry_run = no_publish or not (create_draft or auto_publish)
        result = self.create_topic_draft(topic, query, paper_url, days, top_k, dry_run=dry_run)
        if auto_publish and not no_publish:
            media_id = result["draft"].get("media_id")  # type: ignore[union-attr]
            if media_id:
                result["publish"] = {"publish_id": WechatClient(dry_run=False).publish_draft(str(media_id))}
        return result

    def publish_existing_article(self, article_json: Path, real_wechat: bool, publish: bool) -> dict[str, object]:
        article = Article.from_dict(read_json(article_json, {}))
        client = WechatClient(dry_run=not real_wechat)
        report = client.create_draft(article)
        if publish and real_wechat and report.get("media_id"):
            report["publish_id"] = client.publish_draft(str(report["media_id"]))
        return report

    def update_existing_draft(self, article_json: Path, media_id: str, real_wechat: bool, index: int = 0) -> dict[str, object]:
        article = Article.from_dict(read_json(article_json, {}))
        return WechatClient(dry_run=not real_wechat).update_draft(article, media_id, index)

    def preflight(self) -> dict[str, object]:
        optional = {}
        for module in ("requests", "markdown", "pypdf", "fitz", "PIL", "mcp"):
            try:
                __import__(module)
                optional[module] = True
            except ImportError:
                optional[module] = False
        return {
            "settings": runtime_settings(),
            "python": {"version": sys.version.split()[0], "mcp_supported": sys.version_info >= (3, 10)},
            "optional_dependencies": optional,
        }

    def _resolve_paper(self, topic: str | None, query: str | None, paper_url: str | None, days: int, top_k: int) -> PaperMeta:
        if paper_url:
            paper_id = paper_url.rstrip("/").split("/")[-1]
            return PaperMeta(paper_id=paper_id, title=f"Paper {paper_id}", authors=[], abstract="", source="url", url=paper_url, pdf_url=paper_url.replace("/abs/", "/pdf/"), published_at="")
        papers = [PaperMeta.from_dict(item) for item in self.collect(topic, query, days, ["arxiv"], max_results=max(top_k * 10, 20))]
        ranked = self.rank(papers, top_k=top_k, query=query or topic)
        if not ranked:
            raise RuntimeError("No papers collected. Try a broader query or longer --days window.")
        return PaperMeta.from_dict(ranked[0]["paper"])  # type: ignore[arg-type]


def _article_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def append_figures(markdown: str, figure_paths: list[str]) -> str:
    blocks = ["\n## 论文图表候选\n"]
    for index, path in enumerate(figure_paths, start=1):
        blocks.append(f"![论文图表候选 {index}]({path})")
    return markdown.rstrip() + "\n\n" + "\n\n".join(blocks) + "\n"
