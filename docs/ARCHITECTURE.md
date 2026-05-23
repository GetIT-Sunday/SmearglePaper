# SmearglePaper Architecture

The project follows a small pipeline:

```text
collect -> rank -> read/PDF figures -> staged writing -> render -> cover -> WeChat assets -> draft
```

## Modules

- `collector.py`: arXiv Atom API integration.
- `ranker.py`: deterministic relevance and freshness scoring.
- `reader.py`: PDF download, optional `pypdf` parsing, and optional PyMuPDF figure extraction.
- `llm.py`: three-stage OpenAI-compatible article writer with local fallback.
- `renderer.py`: WeChat-friendly HTML rendering.
- `cover.py`: local cover image generation with Pillow.
- `wechat.py`: WeChat cover upload, content image upload, draft, draft update, and publish API calls.
- `workflow.py`: orchestration used by the CLI.
- `src/mcp_server/server.py`: MCP tools that expose the pipeline over stdio.

## Production Boundary

The stable local boundary is article generation plus draft creation.

Real WeChat calls require:

```bash
WECHAT_APP_ID=...
WECHAT_APP_SECRET=...
```

Real LLM writing requires:

```bash
OPENAI_BASE_URL=...
OPENAI_API_KEY=...
OPENAI_MODEL=...
```

## MCP Tools

Run:

```bash
python -m mcp_server.server
```

This requires Python 3.10+ because the upstream MCP Python SDK no longer publishes compatible builds for Python 3.9.

The server exposes `preflight`, `collect_papers`, `rank_latest`, `read_paper`, `write_article`, `create_draft`, `publish_article`, and `update_draft`.
