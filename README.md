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

## Agent runtime options

Set environment variables to toggle behavior when running `nexus_agent.agent_loop`:

- `NEXUS_USE_LIVE_APIS` = `true|false`
  - When true and `WORKDRIVE_FOLDER_ID` is set, lists files from Zoho WorkDrive and drafts email output for any issues found.
- `WORKDRIVE_FOLDER_ID` = `<folder_id>`
  - Required when using live WorkDrive listing.
- `NEXUS_LIST_PROJECTS` = `true|false`
  - When true, the agent lists projects from Zoho Projects for the portal specified below.
- `ZOHO_PORTAL_ID` = `<portal_id>`
  - Portal identifier for Zoho Projects listing.

Zoho credentials and endpoints are read from environment via `nexus_agent.config.load_zoho_config()`:

- `ZOHO_CLIENT_ID`, `ZOHO_CLIENT_SECRET`, `ZOHO_REFRESH_TOKEN` (required)
- `ZOHO_SCOPES` (space-separated scopes used when authorizing the refresh token)
- `ZOHO_REDIRECT_URI` (must match the URI configured in Zoho Developer Console)
- `ZOHO_ACCOUNTS_BASE` (region base; default `https://accounts.zoho.com`)

### Task creation and retries

- `NEXUS_CREATE_TASKS` = `true|false`
  - When true, the agent creates a Zoho Projects task per document/file with issues.
  - Requires `ZOHO_PORTAL_ID` and `ZOHO_PROJECT_ID`.
- `ZOHO_PROJECT_ID` = `<project_id>`
  - Target project for task creation.
- Retry/backoff tunables:
  - `NEXUS_RETRY_ATTEMPTS` (default `3`, range `1-10`)
  - `NEXUS_RETRY_BASE_DELAY_MS` (default `500` ms)
  - `NEXUS_TASKS_RPS` (task creation rate limit; default `2.0` rps, min `0.1`)

Behavior:

- The agent applies jittered exponential backoff to WorkDrive listing and Projects task creation.
- Per-run task de-duplication prevents creating duplicate tasks for the same `(portal, project, title)`
  combination within one execution.
