# Contributing Guide

This project follows the Global Development Rules documented in this repo. Please read this guide before opening a PR.

## Development environment

- Python: 3.11+
- Package manager: uv
- Linting: Ruff (select = ["E","F","B","I","UP","SIM"], line length 100)
- Formatting: Ruff format + Prettier (for JS/TS)
- Tests: pytest (fast unit tests <100ms/test). E2E: Playwright (TS).

## Getting started

```bash
# Install uv if needed: https://docs.astral.sh/uv/
uv sync --extra dev
pre-commit install --install-hooks
```

## Running quality checks

```bash
# Lint + format (auto-fix where possible)
uv run ruff check .
uv run ruff format .

# Run tests with coverage (goal: >= 80% for new code)
uv run pytest -q --cov=nexus_agent --cov-report=term-missing --cov-fail-under=80
```

## Commit style

- Use Conventional Commits: feat:, fix:, docs:, chore:, refactor:, test:, ci: …
- Keep commits small and focused. All commits must pass pre-commit hooks.

## Security

- Follow OWASP ASVS L2.
- Never commit secrets (.env is ignored). detect-secrets runs pre-commit.
- If a secret leaks, rotate immediately and open a security advisory if needed.

## Pull requests

- PRs require at least one approval and passing CI.
- Block merge if Ruff Bugbear B2 or critical SCA findings.
- Add tests for new features/bugfixes. Maintain >=80% coverage.
- Describe changes clearly and link issues.

## Testing standards

- Unit tests: fast (<100ms/test), deterministic.
- Integration tests: use pytest fixtures for setup/teardown.
- E2E: Playwright TS. Keep tests stable and deterministic.

## Branching

- No direct pushes to main.
- Create feature branches from latest main and open a PR.

## Releasing

- Squash & merge recommended. Use conventional commit scope for changelog generation.

## Contact

- Code owners: see `.github/CODEOWNERS`.
