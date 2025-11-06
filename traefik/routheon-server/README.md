# routheon-server

Lightweight summary service that aggregates `/v1/models` responses from every Traefik mapping and exposes both `/v1/models` and `/stats`.

## Installation

```bash
cd traefik/routheon-server
python3 -m venv .venv
. .venv/bin/activate
pip install .
```

This installs the package and exposes a `routheon-server` console script in the virtual environment. You can now run:

```bash
routheon-server --help
```

## Development

- Keep dependencies minimal (`psutil`, `pyyaml`).
- Run `ruff` on modified files when contributing.
- Build the Docker image with `docker build` or let `docker compose` handle it; the image installs the package and runs the `routheon-server` console entrypoint.
