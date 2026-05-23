from __future__ import annotations

import datetime as dt
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .models import PaperMeta

ARXIV_API = "https://export.arxiv.org/api/query"


class ArxivCollector:
    def collect(self, topic: str | None, query: str | None, days: int, max_results: int) -> list[PaperMeta]:
        search = query or topic_query(topic)
        params = urllib.parse.urlencode(
            {
                "search_query": search,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
                "start": 0,
                "max_results": max_results,
            }
        )
        with urllib.request.urlopen(f"{ARXIV_API}?{params}", timeout=30) as response:
            xml = response.read()
        papers = parse_arxiv_feed(xml)
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
        return [paper for paper in papers if _parse_date(paper.published_at) >= cutoff]


def topic_query(topic: str | None) -> str:
    if not topic or topic == "latest_ai":
        return "cat:cs.AI OR cat:cs.CL OR cat:cs.LG OR cat:cs.CV"
    return topic


def parse_arxiv_feed(xml: bytes) -> list[PaperMeta]:
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(xml)
    papers: list[PaperMeta] = []
    for entry in root.findall("atom:entry", ns):
        paper_url = _text(entry, "atom:id", ns)
        paper_id = paper_url.rstrip("/").split("/")[-1]
        pdf_url = None
        for link in entry.findall("atom:link", ns):
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href")
        papers.append(
            PaperMeta(
                paper_id=paper_id,
                title=_compact(_text(entry, "atom:title", ns)),
                authors=[_text(author, "atom:name", ns) for author in entry.findall("atom:author", ns)],
                abstract=_compact(_text(entry, "atom:summary", ns)),
                source="arxiv",
                url=paper_url,
                pdf_url=pdf_url or paper_url.replace("/abs/", "/pdf/"),
                published_at=_text(entry, "atom:published", ns),
                updated_at=_text(entry, "atom:updated", ns),
                categories=[cat.attrib.get("term", "") for cat in entry.findall("atom:category", ns)],
                keywords=[],
            )
        )
    return papers


def _text(node: ET.Element, selector: str, ns: dict[str, str]) -> str:
    found = node.find(selector, ns)
    return found.text.strip() if found is not None and found.text else ""


def _compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_date(value: str) -> dt.datetime:
    if not value:
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))

