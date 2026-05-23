from __future__ import annotations

import html
import re


class WechatRenderer:
    def render(self, markdown: str) -> str:
        try:
            import markdown as md

            body = md.markdown(markdown, extensions=["extra", "sane_lists"])
        except ImportError:
            body = basic_markdown(markdown)
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SmearglePaper Article</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #1f2933; line-height: 1.78; }}
    .smearglepaper {{ max-width: 760px; margin: 0 auto; padding: 24px 18px; }}
    h1 {{ font-size: 28px; line-height: 1.25; margin: 0 0 18px; }}
    h2 {{ font-size: 20px; border-left: 4px solid #2563eb; padding-left: 10px; margin-top: 30px; }}
    p {{ margin: 14px 0; }}
    blockquote {{ margin: 18px 0; padding: 12px 16px; background: #f6f8fb; border-left: 4px solid #8aa4d6; }}
    code {{ background: #f1f5f9; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body><main class="smearglepaper">{body}</main></body>
</html>"""


def basic_markdown(markdown: str) -> str:
    lines = []
    for line in markdown.splitlines():
        escaped = html.escape(line)
        if escaped.startswith("# "):
            lines.append(f"<h1>{escaped[2:]}</h1>")
        elif escaped.startswith("## "):
            lines.append(f"<h2>{escaped[3:]}</h2>")
        elif escaped.startswith("- "):
            lines.append(f"<p>• {escaped[2:]}</p>")
        elif escaped.strip():
            lines.append(f"<p>{escaped}</p>")
    return re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", "\n".join(lines))
