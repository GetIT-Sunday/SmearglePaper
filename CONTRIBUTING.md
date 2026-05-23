# Contributing

Thanks for helping improve SmearglePaper.

## Development Setup

```bash
conda env create -p ./.conda/envs/smearglepaper -f environment.yml
conda run -p ./.conda/envs/smearglepaper python -m pip install -e ".[dev]"
conda run -p ./.conda/envs/smearglepaper python -m pytest -q
```

## Guidelines

- Keep generated runtime files under `data/` and out of commits.
- Prefer deterministic tests that do not require network access.
- Do not commit credentials or `.env`.
- Keep WeChat real API calls behind explicit dry-run/real-run controls.

