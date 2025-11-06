# routheon-server

`routheon-server` aggregates `/v1/models` responses from every Traefik mapping and serves both `/v1/models` and `/stats`
endpoints behind a single HTTP server.

## Installation

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install .
```

The installation registers a `routheon-server` console script inside the virtual environment. Check the available
options with:

```bash
routheon-server --help
```

## Usage

```bash
routheon-server \
  --mappings /etc/traefik/mappings \
  --host 127.0.0.1 \
  --port 9080 \
  --stats-config-file /etc/traefik/routheon-stats.yml
```

### Command-line options

- `--mappings`: Directory containing Traefik mapping files (default: `/etc/traefik/mappings`)
- `--host`: Bind address for the HTTP server (`127.0.0.1` recommended outside containers)
- `--port`: Listening port (default: `9080`)
- `--skip-mapping`: Regex patterns for mapping filenames to exclude (repeatable, default: `["routheon-server.yml"]`)
- `--mapping-timeout`: Timeout in seconds for querying each backend (default: `2`)
- `--log-level`: Logging verbosity (`DEBUG`…`CRITICAL`, default: `WARNING`)
- `--stats-config-file`: Optional YAML file that disables selected `/stats` fields

## `/stats` configuration

Create a YAML file to hide sensitive sections or fields:

```yaml
# ~/.routheon/stats-config.yml
enabled_sections:
  - system
  - cpu
  - memory
enabled_fields:
  memory:
    - available
    - percent
```

Point the server to it with `--stats-config-file ~/.routheon/stats-config.yml`.  
Only sections listed in `enabled_sections` are exposed; `enabled_fields` trims the corresponding section payload to the
named keys.  
Omit `enabled_sections` to keep all sections while still restricting specific fields.
