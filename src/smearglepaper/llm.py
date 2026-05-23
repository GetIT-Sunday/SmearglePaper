from __future__ import annotations

import json
import urllib.request

from .config import env
from .models import PaperMeta


class ArticleWriter:
    def write(self, paper: PaperMeta, parsed: dict[str, object] | None = None) -> str:
        context = build_context(paper, parsed)
        if env("OPENAI_API_KEY") and env("OPENAI_BASE_URL"):
            try:
                notes = self._call_model("你是严谨的论文阅读助手，只输出结构化中文要点。", notes_prompt(paper, context), temperature=0.2)
                outline = self._call_model("你是科技文章编辑，只输出清晰的文章大纲。", outline_prompt(paper, notes), temperature=0.3)
                return self._call_model("你是严谨的中文科技作者，输出适合微信公众号的 Markdown 深度解读。", article_prompt(paper, notes, outline), temperature=0.45)
            except Exception:
                pass
        return self._write_locally(paper, context)

    def _call_model(self, system: str, user: str, temperature: float) -> str:
        base = env("OPENAI_BASE_URL").rstrip("/")
        payload = {
            "model": env("OPENAI_MODEL", "deepseek-chat"),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        req = urllib.request.Request(
            f"{base}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {env('OPENAI_API_KEY')}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

    def _write_locally(self, paper: PaperMeta, context: str) -> str:
        authors = "、".join(paper.authors[:5]) or "作者未列出"
        categories = "、".join(paper.categories) or "未标注"
        abstract = paper.abstract or "当前只提供了论文链接，尚未抓取到摘要。可以先运行 read 命令解析 PDF，再生成更完整的版本。"
        method_hint = _sentence(context, ["propose", "introduce", "method", "framework", "approach"])
        experiment_hint = _sentence(context, ["experiment", "benchmark", "dataset", "outperform", "improve"])
        return f"""# {paper.title}

> 这是一篇由 SmearglePaper 多阶段本地流程生成的论文解读草稿。配置 OpenAI 兼容模型后，会自动执行“阅读笔记 -> 大纲 -> 成文”的三段式写作。

## 一句话结论

这篇论文围绕 **{paper.title}** 展开，值得关注的原因在于它切中了近期 AI 研究中“能力提升、系统可用性与评测可信度”之间的张力。

## 论文信息

- 论文编号：{paper.paper_id}
- 作者：{authors}
- 来源：{paper.source}
- 类别：{categories}
- 链接：{paper.url}

## 研究问题

作者试图回答的问题可以概括为：在当前模型与数据条件下，怎样让系统在目标任务上表现得更强、更稳定，或者更容易被实际使用。

## 方法概览

从摘要看，论文的核心贡献可以拆成三层：第一，提出或整理了一个明确的问题设定；第二，给出面向该问题的模型、训练、推理或评测方案；第三，通过实验比较说明该方案相对已有方法的优势与边界。

{method_hint}

## 关键发现

{abstract}

{experiment_hint}

## 图表线索

如果 `read` 命令成功抽取 PDF 图表，系统会把候选图片写入 `data/figures/`，后续创建真实微信草稿时可自动上传正文图片。

## 为什么重要

如果这项工作能被复现，它可能对后续研究产生两类影响：一是提供新的实验基线，二是把一个原本分散的技术问题收束成更清晰的工程流程。

## 局限与风险

- 仅凭摘要无法确认全部实验细节，关键结论需要回到论文正文和消融实验。
- 如果数据集、提示词或评测脚本没有公开，复现可信度会下降。
- 对公众号读者来说，最需要警惕的是把单一 benchmark 的提升误读成通用能力跃迁。

## 读者可以继续追问

- 实验设置是否覆盖真实使用场景？
- 数据集或评测指标是否存在偏差？
- 方法收益来自新算法，还是来自更强的数据与调参？
- 代码、模型或数据是否足以支持独立复现？
"""


def build_context(paper: PaperMeta, parsed: dict[str, object] | None = None) -> str:
    chunks = [paper.abstract]
    if parsed:
        chunks.append(str(parsed.get("text", ""))[:12000])
    return "\n\n".join(chunk for chunk in chunks if chunk).strip()


def notes_prompt(paper: PaperMeta, context: str) -> str:
    return f"""请基于以下论文元数据，写一篇中文微信公众号深度解读。

要求：
1. 提取研究问题、核心方法、实验设置、关键结果、局限性；
2. 区分论文明确声称与推断；
3. 不要编造论文中没有的信息。

标题：{paper.title}
作者：{", ".join(paper.authors)}
摘要：{paper.abstract}
分类：{", ".join(paper.categories)}
链接：{paper.url}
正文片段：{context[:12000]}
"""


def outline_prompt(paper: PaperMeta, notes: str) -> str:
    return f"""请把论文阅读笔记改写成微信公众号文章大纲。

标题：{paper.title}
阅读笔记：
{notes}
"""


def article_prompt(paper: PaperMeta, notes: str, outline: str) -> str:
    return f"""请根据阅读笔记和大纲，写一篇中文微信公众号 Markdown 深度解读。

要求：
1. 标题克制，不夸张；
2. 包含：一句话结论、研究问题、方法概览、关键实验、局限性、适合谁读；
3. 保留论文链接；
4. 不编造实验数字；
5. 语言清楚，有技术密度但适合研究生和工程师阅读。

论文标题：{paper.title}
论文链接：{paper.url}
阅读笔记：
{notes}

文章大纲：
{outline}
"""


def _sentence(context: str, keywords: list[str]) -> str:
    for sentence in context.replace("\n", " ").split(". "):
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in keywords) and len(sentence) > 40:
            return sentence.strip() + "."
    return ""
