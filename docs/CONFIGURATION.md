# Configuration

SmearglePaper works without secrets in dry-run mode. Real LLM writing and WeChat draft creation require environment variables.

## LLM

```bash
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=...
OPENAI_MODEL=deepseek-chat
```

The LLM endpoint must be OpenAI-compatible and support `/v1/chat/completions`.

## WeChat

```bash
WECHAT_APP_ID=...
WECHAT_APP_SECRET=...
```

Real WeChat draft creation uploads the generated cover as `thumb_media_id` and uploads extracted figures as content images.

## Dry Run

Use `--dry-run` while developing:

```bash
smearglepaper draft --query "LLM reasoning" --dry-run
```

