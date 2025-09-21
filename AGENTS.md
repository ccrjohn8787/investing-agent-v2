# Repository Guidelines

## Project Structure & Module Organization
- Use a simple, predictable layout:
  - `src/` application code (packages/modules under `src/investing_agent/` when using Python).
  - `tests/` unit and integration tests mirroring `src/` layout.
  - `scripts/` developer utilities (format, data refresh, bootstrap).
  - `configs/` configuration files (YAML/TOML), plus `env/` for `.env.example`.
  - `docs/` architecture notes and runbooks; `assets/` for static files.
- Prefer small, focused modules; avoid long files (>300 lines) when possible.

## Build, Test, and Development Commands
- We standardize on `make` targets. If no `Makefile` exists yet, use the underlying commands shown.
  - `make setup` → create venv and install deps (Python: `python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`).
  - `make run` → run the app locally (e.g., `python -m investing_agent.cli`).
  - `make test` → run tests with coverage (e.g., `pytest -q --cov=src`).
  - `make lint` → static checks (e.g., `ruff check src tests && mypy src`).
  - `make fmt` → auto-format (e.g., `ruff format`).

## Coding Style & Naming Conventions
- Python: 4‑space indent, UTF‑8, type hints required for public functions.
- Naming: `snake_case` for functions/vars, `PascalCase` for classes, `UPPER_SNAKE` for constants, package names all‑lowercase.
- Imports: standard → third‑party → local; keep sorted. Avoid wildcard imports.
- Tools: `ruff` (lint+format), `mypy` (typing). Keep CI clean with zero warnings.

## Testing Guidelines
- Framework: `pytest` with `pytest-cov`. Target ≥80% line coverage for changed code.
- Place tests under `tests/` mirroring `src/` (e.g., `tests/investing_agent/test_cli.py`).
- Name tests `test_*.py`; use fixtures and parametrization; avoid network calls—mock them.
- Run locally: `make test` or `pytest -q`.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Commits should be small and focused; include rationale when not obvious.
- PRs: clear description, linked issues (`Closes #123`), screenshots/logs if relevant, and a short test plan. Keep passing CI.

## Security & Configuration Tips
- Do not commit secrets. Use `.env` locally and provide `env/.env.example` with placeholders.
- Keep API keys in environment variables; document required variables in `README.md`.

## Agent‑Specific Notes
- Follow this guide when generating files. Prefer `src/` layout, write tests alongside changes, and keep formatting/linting clean.
