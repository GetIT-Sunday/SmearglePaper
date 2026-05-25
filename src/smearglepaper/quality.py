from __future__ import annotations

import re
from pathlib import Path

from .models import Article
from .storage import read_json

REQUIRED_SECTIONS = ["一句话结论", "研究问题", "方法", "关键", "局限", "适合谁读"]
RISKY_PHRASES = ["首次", "彻底", "颠覆", "完全解决", "革命性", "显著优于所有", "证明了"]


def review_article_file(path: Path) -> dict[str, object]:
    if path.suffix == ".json":
        article = Article.from_dict(read_json(path, {}))
        markdown = article.markdown
        title = article.title
        figure_count = len(article.figure_paths)
    else:
        markdown = path.read_text(encoding="utf-8")
        title = _title_from_markdown(markdown)
        figure_count = markdown.count("![")

    issues: list[dict[str, str]] = []
    suggestions: list[str] = []
    char_count = len(markdown)
    headings = re.findall(r"^#{1,3}\s+(.+)$", markdown, flags=re.MULTILINE)

    if char_count < 2500:
        issues.append({"severity": "medium", "message": "文章偏短，适合作为快读稿；若要公众号深度解读，建议扩到 3000-5000 字。"})
    if char_count > 9000:
        issues.append({"severity": "medium", "message": "文章偏长，公众号阅读压力较大，建议拆分或压缩。"})
    if not title or len(title) < 10:
        issues.append({"severity": "high", "message": "标题信息量不足。"})
    if len(title) > 64:
        issues.append({"severity": "low", "message": "标题较长，可能不适合公众号列表页展示。"})

    missing = [name for name in REQUIRED_SECTIONS if not any(name in heading for heading in headings)]
    if missing:
        issues.append({"severity": "medium", "message": "缺少或未明确标出的栏目：" + "、".join(missing)})

    risky_hits = [phrase for phrase in RISKY_PHRASES if phrase in markdown]
    if risky_hits:
        issues.append({"severity": "medium", "message": "存在可能过度断言的词：" + "、".join(risky_hits)})
        suggestions.append("将强断言改成“作者认为/结果显示/在该设置下”，避免超出论文证据。")

    if figure_count == 0:
        issues.append({"severity": "low", "message": "没有图表候选。公众号可读性会弱一些。"})
    elif "page_1_preview" in markdown:
        issues.append({"severity": "low", "message": "当前图表候选是首页预览，不一定是论文核心图。"})

    if "http://arxiv.org/abs/" not in markdown and "https://arxiv.org/abs/" not in markdown:
        issues.append({"severity": "medium", "message": "未检测到 arXiv 论文链接。"})

    score = 100
    for issue in issues:
        score -= {"high": 25, "medium": 12, "low": 5}.get(issue["severity"], 5)
    score = max(score, 0)

    if score >= 85:
        verdict = "ready_after_light_edit"
    elif score >= 70:
        verdict = "needs_editorial_pass"
    else:
        verdict = "needs_revision"

    if not suggestions:
        suggestions = [
            "检查摘要中的关键实验数字是否和论文原文一致。",
            "为公众号读者补一个“为什么现在值得读”的现实背景段。",
            "发布前确认图表是否为核心图，而不是 PDF 首页预览。",
        ]

    return {
        "path": str(path),
        "title": title,
        "char_count": char_count,
        "heading_count": len(headings),
        "figure_count": figure_count,
        "score": score,
        "verdict": verdict,
        "issues": issues,
        "suggestions": suggestions,
    }


def _title_from_markdown(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""

