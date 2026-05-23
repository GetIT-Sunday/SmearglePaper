from __future__ import annotations

import datetime as dt
import re

from .models import PaperMeta


def rank_papers(papers: list[PaperMeta], query: str | None = None, top_k: int = 5) -> list[dict[str, object]]:
    terms = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]+|[\u4e00-\u9fff]{2,}", query or "large language model ai reasoning agent multimodal"))
    rows = []
    now = dt.datetime.now(dt.timezone.utc)
    for paper in papers:
        haystack = f"{paper.title} {paper.abstract} {' '.join(paper.categories)}".lower()
        relevance = sum(1 for term in terms if term.lower() in haystack)
        freshness = _freshness(now, paper.published_at)
        category_boost = 1.0 if any(cat.startswith(("cs.AI", "cs.CL", "cs.LG", "cs.CV")) for cat in paper.categories) else 0.0
        score = relevance * 2.0 + freshness + category_boost
        rows.append({"score": round(score, 3), "paper": paper.to_dict(), "reasons": _reasons(relevance, freshness, category_boost)})
    rows.sort(key=lambda row: row["score"], reverse=True)
    return rows[:top_k]


def _freshness(now: dt.datetime, value: str) -> float:
    try:
        published = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    age_days = max((now - published).days, 0)
    return max(0.0, 7.0 - age_days) / 7.0


def _reasons(relevance: int, freshness: float, category_boost: float) -> list[str]:
    reasons = [f"topic_terms={relevance}", f"freshness={freshness:.2f}"]
    if category_boost:
        reasons.append("ai_category")
    return reasons

