# Routheon

Lightweight API_KEY router compatible with the OpenAI protocol.  
Route multiple `llama.cpp` model servers through a single API endpoint using Traefik.

---

## Overview

Routheon acts as a reverse proxy that exposes one unified API endpoint (OpenAI compatible) and routes incoming API
requests to different `llama.cpp` model servers based on the provided API key.

This enables per-user or per-model access control while keeping the architecture simple.

---

## Use Cases

- Run multiple `llama.cpp` servers behind a single API
- Provide per-user or per-model access via API keys
- Simplify client integration using an OpenAI-compatible endpoint

### Optional Routheon Server

routheon-server is a lightweight companion process that exposes two helper endpoints:

- `/v1/models`: Aggregates every reachable `llama.cpp` backend into one OpenAI-compatible list
- `/stats`: Shows basic host metrics (CPU, RAM, uptime) for the machine running the aggregator

The core router works without this service, but enabling it gives you instant visibility into which models are online
and the metrics of the host that serves them.

---

## Architecture

```text
                   ┌────────────────────────────┐
                   │        Traefik Router      │
                   │   (port 8080, /v1/...)     │
                   └──────────────┬─────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────────┐
        │                         │                             │
        ▼                         ▼                             ▼
┌──────────────────┐     ┌──────────────────┐     ┌────────────────────────┐
│ llama-server-1   │     │ llama-server-2   │     │    routheon-server     │
│ TinyLlama_Chat   │     │ mistral-tiny     │     │ (optional, port 9080)  │
│ (API_KEY-1)      │     │ (API_KEY-2)      │     │ /v1/models + /stats    │
└──────────────────┘     └──────────────────┘     │ aggregate + host info  │
        ▲                         ▲               └────────────────────────┘
        │                         │                             ▲
        │                         │                             │
     with API_KEY: /v1/chat/completions, ...                    |
                                                                |
                                                  without API_KEY: /v1/models 
```

The diagram above illustrates how Routheon routes incoming requests.  
All traffic **with** an API key is forwarded by Traefik to the corresponding `llama.cpp` backend.  
Requests to `/v1/models` or `/stats` **without** an API key are handled by the **optional routheon-server**,  
which aggregates model metadata and host statistics across all reachable backends.


---

## Routheon Demo

The Routheon demo stack sets up an API_KEY router using [Traefik](https://doc.traefik.io/traefik/) and includes
two [llama.cpp](https://github.com/ggml-org/llama.cpp) servers with small models.

### Prerequisites

- Docker Compose
- requires less than 1 GB of disk space (see [Clean-up after the Demo](#clean-up-after-the-demo))

### Demo Setup

#### Clone the Repository

```bash
git clone git@github.com-Wuodan:Wuodan/routheon.git
cd routheon
```

#### Run the Docker Compose File

```bash
docker compose up -d
```

Wait for all `llama-server` services to be `healthy`. The models must be downloaded before the services are fully
operational.

To check status, run:

```bash
docker compose ps
```

### Demo Requests

Use the following `curl` commands to exercise the setup with `API_KEY-1` and `API_KEY-2`.

**For API_KEY-1 and routing to llama-server-1 (model=TinyLlama_Chat):**

```bash
curl http://127.0.0.1:8080/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer API_KEY-1" \
-d '{
   "model": "TinyLlama_Chat",
   "messages": [
      {"role": "system", "content": "You are a concise assistant."},
      {"role": "user", "content": "Write a one-line Python function that prints hello."}
   ]
 }'
```

**For API_KEY-2 and routing to llama-server-2 (model=mistral-tiny):**

```bash
curl http://127.0.0.1:8080/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer API_KEY-2" \
-d '{
   "model": "mistral-tiny",
   "messages": [
      {"role": "system", "content": "You are a concise assistant."},
      {"role": "user", "content": "Write a one-line Python function that prints hello."}
   ]
 }'
 ```

#### Demo: Routheon Server `/v1/models`

In this demo stack, routheon-server is already enabled.  
You can inspect which llama.cpp backends are up using `/v1/models`.

##### Without API key: See all active models

Returns all models from all reachable llama.cpp servers:

```bash
curl http://127.0.0.1:8080/v1/models
```

##### With API key: See model of one llama-server

Returns only the models available behind that specific key / backend:

```bash
curl http://127.0.0.1:8080/v1/models \
-H "Authorization: Bearer API_KEY-1"
```

##### Supports inactive llama-server

You can stop one of the llama-servers and the routheon-server endpoint will show only one model:

```bash
docker compose stop llama-server-2
curl http://127.0.0.1:8080/v1/models
docker compose start llama-server-2
```

#### Demo: Routheon Server `/stats`

routheon-server also serves `/stats`, which returns CPU, memory, disk, network, and uptime information for the host
running the aggregator.

This is configured to see only a subset of the available information.  
See [Configure `/stats` output](#configure-stats-output) below.

```bash
curl http://127.0.0.1:8080/stats | jq
```

Use it to monitor resource pressure before launching additional llama.cpp servers.

### Clean-up after the Demo

The models are stored in a Docker volume. When you are done with the demo, delete images and the volume with:

```bash
# docker clean-up
docker compose down
docker image rm traefik:latest ghcr.io/ggml-org/llama.cpp:server python:slim routheon_routheon-server:demo

# archived during demo as it contains API_KEY-2
mv traefik/mappings/llama-server-3.yml{.bak.*,} 2>/dev/null

# created during demo
[ -f traefik/mappings/llama-server-2.yml ] && \
  sudo rm traefik/mappings/llama-server-2.yml
```

Remove the volume with the models:

```bash
docker volume rm routheon_llama_cpp
```

---

## Routheon in Production

This describes a bare-metal setup without Docker. Both `traefik` and `llama.cpp` run on the same computer.

### Prerequisites

- Install [Traefik](https://doc.traefik.io/traefik/getting-started/install-traefik/)
- Install [llama.cpp](https://github.com/ggml-org/llama.cpp#quick-start) to have one or several instances of
  `llama-server` with dedicated ports
- Python: if you want the [Optional Routheon Server](#optional-routheon-server)

### Installation

#### Traefik Config: `traefik.yml`

1. Copy [`traefik/traefik.yml`](traefik/traefik.yml) to `/etc/traefik/traefik.yml`
   ```bash
   sudo mkdir -p /etc/traefik
   sudo curl -LO --output-dir /etc/traefik https://raw.githubusercontent.com/Wuodan/routheon/refs/heads/main/traefik/traefik.yml
   sudo mkdir -p /etc/traefik//mappings
   ```
2. Adapt the port to your needs.
3. Add logging (`accessLog`) and other Traefik settings as needed.

#### Traefik Config: Map API_KEY to llama.cpp instance

Here you have 2 choices:

- Dynamic Auto-Mapping: Let mappings be created/updated when `llama-server` starts
- Manual Mapping: Manage the mapping files manually

##### Dynamic Auto-Mapping with `create-mapping.sh`

Change your system daemon for `llama-server` to also call [create-mapping.sh](traefik/create-mapping/create-mapping.sh).

Download script:

```bash
sudo curl -LO --output-dir /usr/local/bin https://raw.githubusercontent.com/Wuodan/routheon/refs/heads/main/traefik/create-mapping/create-mapping.sh
sudo chmod +x /usr/local/bin/create-mapping.sh
```

Example: Chain create-mapping.sh and llama-server:

```bash
/usr/local/bin/create-mapping.sh \
  --port 8011 \
  --service TinyLlama_Chat \
  --api_key 'my-api-key' && \
\
exec \
  llama-server \
      --hf-repo TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF:Q2_K \
      --port 8011 \
      --alias TinyLlama_Chat
```

> This uses defaults for the mapping folder and the host, use `--mappings` and `--host` to set them.

##### Manual Mapping

1. Create mappings in `/etc/traefik/mappings/`
2. For each `llama.cpp` instance, create a `my-server.yml` file
   like [llama-server-1.yml](traefik/mappings/llama-server-1.yml)
    - The `url` must be `http://127.0.0.1:<LLAMA_PORT>`
    - Replace `API_KEY-1` with your own API key for each `llama-server`

#### Traefik Service

- Configure a system daemon for Traefik depending on your OS
- The path of the mappings folder can be changed in `traefik.yml`
- If you choose another path for `traefik.yml`, use the `traefik --configFile <PATH>` parameter

### llama.cpp

Run `llama-server` without the `--host` parameter (so it defaults to `127.0.0.1`) to prevent direct remote access to its
port.

### Ready to Use

- All instances of `llama.cpp` can now be accessed remotely via a single common port
- Access to each instance is controlled by API_KEY

### Optional Routheon Server

The routheon-server companion service collects the `/v1/models` information from all configured
targets and provides both `/v1/models` and `/stats` endpoints back to Traefik.

It’s **optional** — Routheon works normally without it.
Enable it only if you want `/v1/models` to aggregate all active model servers or to expose `/stats`.

The routheon-server aggregates the `/v1/models` output from all reachable `llama.cpp` servers and returns an OpenAI
compatible response as if one server was providing multiple models.

#### Installation

1. Copy [`traefik/mappings/routheon-server.yml`](traefik/mappings/routheon-server.yml) to `/etc/traefik/mappings/` (same
   path as other mappings).  
   In `routheon-server.yml`, change the URL to `http://127.0.0.1:9080`.

   ```bash
   sudo mkdir -p /etc/traefik/mappings/
   cd /etc/traefik/mappings/
   sudo curl -LO https://raw.githubusercontent.com/Wuodan/routheon/refs/heads/main/traefik/mappings/routheon-server.yml
   sudo sed -i.bak 's#http://routheon-server:#http://127.0.0.1:#' routheon-server.yml
   sudo rm -f routheon-server.yml.bak
   ```

2. Install routheon-server into a virtual environment (either from PyPI or from the cloned repo):
   ```bash
   python3 -m venv ~/.routheon/venv
   ~/.routheon/venv/bin/pip install routheon-server
   ```
   For local development builds, run `~/.routheon/venv/bin/pip install .` from the repository root instead.

3. Set up a system daemon depending on your OS to run the installed console script.

   The daemon should run this command:
   ```bash
   ~/.routheon/venv/bin/routheon-server
   ```

#### Customize

The defaults of `routheon-server` suit the described setup.  
If your setup is different, then adapt the command with the following arguments:

- `--mappings`: Directory containing Traefik mapping files (default: `/etc/traefik/mappings`)
- `--host`: Host to bind the HTTP server to. Use `127.0.0.1` (default) for remote access by Traefik only
- `--port`: Port to listen on (default: `9080`). Ensure this matches the URL in the `routheon-server.yml` file
- `--skip-mapping`: YAML filenames to skip (regex patterns, default: `["routheon-server.yml"]`)
    - `routheon-server.yml`: The mapping file for the routheon-server itself must be in that list
    - Add patterns for other mapping files you want to exclude from the aggregation
- `--mapping-timeout`: Timeout in seconds for requests to each mapping (default: `2`)
- `--stats-config-file`: Path to a YAML file that hides selected `/stats` sections or fields
- `--log-level`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`; default: `WARNING`)
- `ROUTHEON_VERSION` build arg: when building the Docker image (e.g., via `docker compose build`), override this arg to
  stamp the desired package version (`docker compose build --build-arg ROUTHEON_VERSION=0.4.0 routheon-server`). The demo
  stack falls back to `0.0.0.dev0`, which is a valid development version for local use.

Example:

```bash
~/.routheon/venv/bin/routheon-server \
  --mappings /etc/traefik/mappings \
  --host 127.0.0.1 \
  --port 9080
```

##### Configure `/stats` output

To see the full output of `/stats` run:

```bash
~/.routheon/venv/bin/routheon-server
```
and read the output in a second terminal with
```bash
curl http://127.0.0.1:9080/stats | jq
```

###### Limit `/stats` output

If `/stats` exposes information you do not want to share, create a YAML configuration file:

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

Start the service with:

```bash
~/.routheon/venv/bin/routheon-server \
  --mappings /etc/traefik/mappings \
  --stats-config-file ~/.routheon/stats-config.yml
```

When a config file is provided, only sections listed in `enabled_sections` are exposed.  
Within each section, `enabled_fields` narrows the dictionary to the listed keys.  
Omit `enabled_sections` to keep all sections but still restrict individual fields.

---

## Releasing `routheon-server`

The Python helper package now derives its version from Git tags via `hatch-vcs`, so there's no manual edit to
`pyproject.toml` when cutting a release. To publish a new version:

1. Ensure `main` already contains the desired commits, then create a tag that matches the version you intend to push,
   e.g. `git tag v0.2.0`.
2. Push the tag (`git push origin v0.2.0`). The GitHub Actions workflow runs lint/tests across supported Python
   versions and, if the push is a tag, builds and uploads to PyPI using that semantic version.
3. (Optional) Draft a GitHub Release pointing at the same tag for humans to discover the changes.

Because PyPI treats releases as immutable, bump the tag (e.g. `v0.2.1`) for any follow-up fixes instead of trying to
replace an existing version.

---

## License & Status

**License:** Apache License 2.0  
**Status:** Experimental / Proof of Concept
