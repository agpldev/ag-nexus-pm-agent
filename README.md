# ag-nexus-pm-agent

agentic AI for the management of the nexus project

## Development

- Python >= 3.11, package manager: `uv`
- Install deps: `uv sync --extra dev`
- Lint/format: `uv run ruff check .` and `uv run ruff format .`
- Tests: `uv run pytest -q --cov=nexus_agent --cov-report=term-missing`

## CI

GitHub Actions workflow at `.github/workflows/ci.yml`:

- Pre-commit hooks (Ruff lint + format, detect-secrets)
- Pytest with coverage (>=80% fail-under)
- Optional OWASP ZAP Baseline scan on PRs when enabled (see below)

## Enabling ZAP Baseline Scan (optional)

1) Add a repository variable `ZAP_TARGET` in GitHub (Settings → Secrets and variables → Variables)
   pointing to the URL to scan, e.g. `https://staging.example.com`.
2) Customize passive scan rule thresholds in `.zap/rules.tsv` (provided). Common noisy rules are set to
   `WARN`/`IGNORE`. See ZAP docs for rule IDs.
3) Open a PR; the "zap-baseline" job will run automatically when `ZAP_TARGET` is set.

Notes:

- The baseline scan is passive (non-invasive). For active scans, run ZAP locally and avoid CI by default.
- The CI job is guarded with `if: ${{ github.event_name == 'pull_request' && vars.ZAP_TARGET != '' }}`.

## Security

- Never commit secrets. `.env` is ignored and repository history has been scrubbed.
- Rotate credentials immediately if a secret ever leaks.

## Contributing

See `CONTRIBUTING.md` and code ownership in `.github/CODEOWNERS`.
