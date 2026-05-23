# MCP

SmearglePaper exposes its paper-to-draft workflow as an MCP server.

## Run Manually

```bash
python -m mcp_server.server
```

When using the project-local conda environment:

```bash
bash scripts/conda-python -m mcp_server.server
```

## Client Configuration

Use the Python executable inside your environment. Example:

```json
{
  "mcpServers": {
    "smearglepaper": {
      "command": "/absolute/path/to/smearglepaper/.conda/envs/smearglepaper/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/absolute/path/to/smearglepaper"
    }
  }
}
```

## Tools

- `preflight`: Check dependencies, Python version, LLM settings, and WeChat settings.
- `collect_papers`: Collect recent arXiv papers and save `data/papers/latest.json`.
- `rank_latest`: Rank papers from the latest local collection.
- `read_paper`: Download and parse a paper from local paper metadata.
- `write_article`: Generate Markdown, HTML, cover, and article JSON for one paper.
- `create_draft`: Run collect/rank/read/write/draft workflow.
- `publish_article`: Create or publish a WeChat draft from an article JSON.
- `update_draft`: Update an existing WeChat draft.

