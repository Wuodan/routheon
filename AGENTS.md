# Repository Guidelines

## Project Structure & Module Organization
- `docker-compose.yml`: Demo stack (Traefik proxy, two llama.cpp servers, optional summary service).
- `traefik/traefik.yml`: Static Traefik config and entrypoint.
- `traefik/mappings/*.yml`: API key → backend mappings (watched by Traefik).
- `traefik/create-mapping/create-mapping.sh`: Generates/rotates mapping files.
- `routheon_server/`: Lightweight Python service aggregating `/v1/models` and `/stats`.

## Build, Test, and Development Commands
- Start demo: `docker compose up -d`
- Check health: `docker compose ps`
- Logs (proxy): `docker compose logs -f traefik-proxy`
- Stop/clean: `docker compose down`
- Run summary service locally:
  `python3 -m venv .venv && . .venv/bin/activate && pip install routheon-server && routheon-server --help`
  (always create/use the shared repo-root `.venv`; do not scatter virtualenvs elsewhere)
- Quick tests:
  - All models: `curl http://127.0.0.1:8080/v1/models`
  - With key: `curl -H "Authorization: Bearer API_KEY-1" http://127.0.0.1:8080/v1/models`

## Coding Style & Naming Conventions
- Python (summary service): PEP 8, 4-space indent, explicit type hints everywhere (functions, variables, attributes). Avoid `Any`; prefer precise types, `TypedDict`/`Protocol`, and `Literal` where applicable. No `type: ignore` unless justified in code review. Use `logging` (no prints). Keep deps minimal (`pyyaml`, `psutil`).
- Bash: `#!/bin/bash`, `set -euo pipefail`, small functions + `usage`, POSIX‑friendly where feasible.
- YAML: 2‑space indent; filenames `*.yml`. Mapping filenames match service name; sanitized to `[A-Za-z0-9._-]` (see script).
- Naming: Traefik service/router names mirror mapping filename; model aliases are simple, lowercase or `Camel_Case` (e.g., `mistral-tiny`, `TinyLlama_Chat`).
- Linting/formatting: run language-specific tools only on touched files—`ruff check routheon_server --fix`, `shellcheck`/`bash -n` for scripts, `yamllint traefik` for YAML, and pick the equivalent best-practice linter/formatter for any other file type you modify—so best-practice rules stay enforced without rewriting the entire repo.

## Testing Guidelines
- No formal test suite. Validate via `curl` and Docker healthchecks.
- For changes to the summary service, exercise `/v1/models` and `/stats`; run with `--log-level DEBUG` for troubleshooting.

## Commit & Pull Request Guidelines
- Commits: short, imperative subject (e.g., "Add endpoint /stats", "Fix typo").
- PRs must include:
  - What changed and why; link issues when applicable.
  - How you tested: commands run and expected outputs (e.g., `docker compose ps`, `curl` responses).
  - Screenshots or logs when altering routing or health.

## Security & Configuration Tips
- Never commit real API keys; use placeholders (`API_KEY-1`).
- In production, keep llama.cpp bound to `127.0.0.1`; expose only Traefik.
- Use `create-mapping.sh` during start of llama-server instances  to safely rotate mappings using the same API key.
