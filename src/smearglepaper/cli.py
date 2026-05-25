from __future__ import annotations

import argparse
import json
from pathlib import Path

from .collector import ArxivRateLimitError, ArxivTemporaryError, topic_names
from .config import DATA_DIR, runtime_settings
from .llm import check_llm_connection
from .models import PaperMeta
from .storage import read_json
from .wechat import WechatClient
from .workflow import SmearglePaperWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="smearglepaper", description="AI paper to Chinese article draft automation")
    sub = parser.add_subparsers(dest="command", required=True)

    collect = sub.add_parser("collect", help="Collect recent papers")
    collect.add_argument("--topic", help=f"Preset topic. Available: {', '.join(topic_names())}")
    collect.add_argument("--query")
    collect.add_argument("--days", type=int, default=7)
    collect.add_argument("--sources", nargs="+", default=["arxiv"])
    collect.add_argument("--max-results", type=int, default=50)

    rank = sub.add_parser("rank", help="Rank collected papers")
    rank.add_argument("--input", default=str(DATA_DIR / "papers" / "latest.json"))
    rank.add_argument("--top-k", type=int, default=5)

    read = sub.add_parser("read", help="Download and parse one paper from latest collection")
    read.add_argument("--paper-id", required=True)

    write = sub.add_parser("write", help="Generate a WeChat Markdown and HTML article")
    write.add_argument("--paper-id", required=True)

    draft = sub.add_parser("draft", help="Generate an article and create a local or real WeChat draft")
    draft.add_argument("--topic", default="latest_ai", help=f"Preset topic. Available: {', '.join(topic_names())}")
    draft.add_argument("--query")
    draft.add_argument("--paper-url")
    draft.add_argument("--days", type=int, default=7)
    draft.add_argument("--top-k", type=int, default=5)
    draft.add_argument("--dry-run", action="store_true")

    auto = sub.add_parser("auto-publish", help="Run the full workflow")
    auto.add_argument("--topic", help=f"Preset topic. Available: {', '.join(topic_names())}")
    auto.add_argument("--query")
    auto.add_argument("--paper-url")
    auto.add_argument("--days", type=int, default=7)
    auto.add_argument("--top-k", type=int, default=5)
    auto.add_argument("--create-draft", action="store_true")
    auto.add_argument("--auto-publish", action="store_true")
    auto.add_argument("--no-publish", action="store_true")

    sub.add_parser("check-config", help="Show runtime configuration")
    sub.add_parser("preflight", help="Check optional dependencies and credentials")
    sub.add_parser("check-llm", help="Check OpenAI-compatible model connectivity")

    publish = sub.add_parser("wechat-publish", help="Create or publish an existing generated article")
    publish.add_argument("--article-json", required=True)
    publish.add_argument("--draft-only", action="store_true")
    publish.add_argument("--publish", action="store_true")
    publish.add_argument("--dry-run", action="store_true")

    update = sub.add_parser("wechat-update-draft", help="Update an existing WeChat draft")
    update.add_argument("--article-json", required=True)
    update.add_argument("--media-id", required=True)
    update.add_argument("--index", type=int, default=0)
    update.add_argument("--dry-run", action="store_true")

    status = sub.add_parser("publish-status", help="Query WeChat publish status")
    status.add_argument("--publish-id", required=True)

    pub_draft = sub.add_parser("publish-draft", help="Submit an existing WeChat draft media_id")
    pub_draft.add_argument("--media-id", required=True)

    sub.add_parser("published-index", help="Show local published index")

    topics = sub.add_parser("topics", help="List built-in topic presets")
    topics.set_defaults(_topics=True)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    workflow = SmearglePaperWorkflow()

    try:
        if args.command == "collect":
            papers = workflow.collect(args.topic, args.query, args.days, args.sources, args.max_results)
            _print({"count": len(papers), "output": str(DATA_DIR / "papers" / "latest.json")})
        elif args.command == "rank":
            papers = workflow.load_papers_file(Path(args.input))
            _print(workflow.rank(papers, top_k=args.top_k))
        elif args.command == "read":
            _print(workflow.read(_find_paper(args.paper_id)))
        elif args.command == "write":
            paper = _find_paper(args.paper_id)
            parsed_path = DATA_DIR / "parsed" / f"{paper.paper_id.replace('/', '_')}.json"
            _print(workflow.write_article(paper, parsed=read_json(parsed_path, {})))
        elif args.command == "draft":
            _print(workflow.create_topic_draft(args.topic, args.query, args.paper_url, args.days, args.top_k, args.dry_run))
        elif args.command == "auto-publish":
            _print(workflow.auto_publish(args.topic, args.query, args.paper_url, args.days, args.top_k, args.create_draft, args.auto_publish, args.no_publish))
        elif args.command == "check-config":
            _print(runtime_settings())
        elif args.command == "preflight":
            _print(workflow.preflight())
        elif args.command == "check-llm":
            _print(check_llm_connection())
        elif args.command == "wechat-publish":
            if not args.draft_only and not args.publish:
                raise SystemExit("Use --draft-only or --publish.")
            _print(workflow.publish_existing_article(Path(args.article_json), real_wechat=not args.dry_run, publish=args.publish))
        elif args.command == "wechat-update-draft":
            _print(workflow.update_existing_draft(Path(args.article_json), args.media_id, real_wechat=not args.dry_run, index=args.index))
        elif args.command == "publish-status":
            _print(WechatClient(dry_run=False).get_publish_status(args.publish_id))
        elif args.command == "publish-draft":
            _print({"publish_id": WechatClient(dry_run=False).publish_draft(args.media_id)})
        elif args.command == "published-index":
            _print(read_json(DATA_DIR / "published_index.json", {}))
        elif args.command == "topics":
            _print({"topics": topic_names()})
    except ArxivRateLimitError as exc:
        raise SystemExit(str(exc)) from exc
    except ArxivTemporaryError as exc:
        raise SystemExit(str(exc)) from exc


def _find_paper(paper_id: str) -> PaperMeta:
    for item in read_json(DATA_DIR / "papers" / "latest.json", []):
        if item.get("paper_id") == paper_id:
            return PaperMeta.from_dict(item)
    for row in read_json(DATA_DIR / "papers" / "ranked_latest.json", []):
        paper = row.get("paper", {})
        if paper.get("paper_id") == paper_id:
            return PaperMeta.from_dict(paper)
    raise SystemExit(f"Paper not found in latest data: {paper_id}")


def _print(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
