from __future__ import annotations

from pathlib import Path

from smearglepaper.config import DATA_DIR
from smearglepaper.models import PaperMeta
from smearglepaper.storage import read_json
from smearglepaper.workflow import SmearglePaperWorkflow

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised by preflight instead
    raise SystemExit("Install MCP support first: python -m pip install -r requirements.txt") from exc

mcp = FastMCP("smearglepaper")


@mcp.tool()
def preflight() -> dict[str, object]:
    """Check local dependencies, LLM settings, and WeChat settings."""
    return SmearglePaperWorkflow().preflight()


@mcp.tool()
def collect_papers(query: str = "", topic: str = "latest_ai", days: int = 7, max_results: int = 20) -> dict[str, object]:
    """Collect recent arXiv papers and save them to data/papers/latest.json."""
    workflow = SmearglePaperWorkflow()
    papers = workflow.collect(topic or None, query or None, days, ["arxiv"], max_results)
    return {"count": len(papers), "output": str(DATA_DIR / "papers" / "latest.json"), "papers": papers}


@mcp.tool()
def rank_latest(query: str = "", top_k: int = 5) -> dict[str, object]:
    """Rank papers from the latest local collection."""
    workflow = SmearglePaperWorkflow()
    papers = workflow.load_papers_file(DATA_DIR / "papers" / "latest.json")
    rows = workflow.rank(papers, top_k=top_k, query=query or None)
    return {"count": len(rows), "output": str(DATA_DIR / "papers" / "ranked_latest.json"), "ranked": rows}


@mcp.tool()
def read_paper(paper_id: str) -> dict[str, object]:
    """Download and parse a paper from the latest/ranked local collection."""
    workflow = SmearglePaperWorkflow()
    return workflow.read(_find_paper(paper_id))


@mcp.tool()
def write_article(paper_id: str) -> dict[str, object]:
    """Generate Markdown, HTML, cover, and article JSON for a local paper."""
    workflow = SmearglePaperWorkflow()
    paper = _find_paper(paper_id)
    parsed_path = DATA_DIR / "parsed" / f"{paper.paper_id.replace('/', '_')}.json"
    return workflow.write_article(paper, parsed=read_json(parsed_path, {}))


@mcp.tool()
def create_draft(query: str = "", topic: str = "latest_ai", paper_url: str = "", days: int = 7, top_k: int = 5, dry_run: bool = True) -> dict[str, object]:
    """Run the full collect-rank-read-write-draft workflow."""
    return SmearglePaperWorkflow().create_topic_draft(topic or None, query or None, paper_url or None, days, top_k, dry_run=dry_run)


@mcp.tool()
def publish_article(article_json: str, draft_only: bool = True, dry_run: bool = True) -> dict[str, object]:
    """Create a WeChat draft from an existing article JSON, optionally submitting publish."""
    return SmearglePaperWorkflow().publish_existing_article(Path(article_json), real_wechat=not dry_run, publish=not draft_only)


@mcp.tool()
def update_draft(article_json: str, media_id: str, index: int = 0, dry_run: bool = True) -> dict[str, object]:
    """Update an existing WeChat draft from an article JSON."""
    return SmearglePaperWorkflow().update_existing_draft(Path(article_json), media_id=media_id, real_wechat=not dry_run, index=index)


def _find_paper(paper_id: str) -> PaperMeta:
    for item in read_json(DATA_DIR / "papers" / "latest.json", []):
        if item.get("paper_id") == paper_id:
            return PaperMeta.from_dict(item)
    for row in read_json(DATA_DIR / "papers" / "ranked_latest.json", []):
        paper = row.get("paper", {})
        if paper.get("paper_id") == paper_id:
            return PaperMeta.from_dict(paper)
    raise ValueError(f"Paper not found in latest data: {paper_id}")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
