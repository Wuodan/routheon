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

### Model Summary Endpoint

Routheon can optionally expose an **OpenAI-compatible `/v1/models` endpoint** that summarizes all reachable `llama.cpp`
servers.  
It provides a quick overview of which models are online and ready.
The output is the same as if one OpenAI compatible server was serving several models.

This feature is optional and requires a small companion service.

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
│ llama-server-1   │     │ llama-server-2   │     │ Model Summary Service  │
│ TinyLlama_Q2     │     │ Mistral-tiny_Q2  │     │ (optional, port 9080)  │
│ (API_KEY-1)      │     │ (API_KEY-2)      │     │ aggregates /v1/models  │
└──────────────────┘     └──────────────────┘     │ across all backends    │
        ▲                         ▲               └────────────────────────┘
        │                         │                             ▲
        │                         │                             │
        │                         │                    /v1/models (no API_KEY)
        │                         │
        └────────────── /v1/chat/completions, /v1/models (with API_KEY)
```

The diagram above illustrates how Routheon routes incoming requests.  
All traffic **with** an API key is forwarded by Traefik to the corresponding `llama.cpp` backend.  
Requests to `/v1/models` **without** an API key are handled by the **optional Model Summary Service**,  
which aggregates the `/v1/models` outputs from all reachable backends.


---

## Routheon Test

The Routheon test sets up an API_KEY router using [Traefik](https://doc.traefik.io/traefik/) and includes
two [llama.cpp](https://github.com/ggml-org/llama.cpp) servers with small models.

### Prerequisites

- Docker Compose
- less than 1GB disk space

### Test Setup

#### Clone the Repository

```bash
git clone git@github.com-Wuodan:Wuodan/routheon.git
cd routheon
```

#### Run the Docker Compose File

```bash
docker-compose up -d
```

Wait for all `llama-server` services to be `healthy`. The models must be downloaded before the services are fully
operational.

To check status, run:

```bash
docker compose ps
```

#### Clean-up after Test

The models are stored in a Docker volume. When you are done testing, delete images and the volume with:

```bash
docker compose down
docker image rm traefik:latest ghcr.io/ggml-org/llama.cpp:server python:slim routheon_all-models:latest
docker volume rm routheon_llama_cpp
```

### Test Requests

Use the following `curl` commands to test the setup with `API_KEY-1` and `API_KEY-2`.

**For API_KEY-1 and routing to llama-server-1 (model=TinyLlama_Q2):**

```bash
curl http://127.0.0.1:8080/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer API_KEY-1" \
-d '{
   "model": "TinyLlama_Q2",
   "messages": [
      {"role": "system", "content": "You are a concise assistant."},
      {"role": "user", "content": "Write a one-line Python function that prints hello."}
   ]
 }'
```

**For API_KEY-2 and routing to llama-server-2 (model=mistral-tiny_Q2):**

```bash
curl http://127.0.0.1:8080/v1/chat/completions \
-H "Content-Type: application/json" \
-H "Authorization: Bearer API_KEY-2" \
-d '{
   "model": "mistral-tiny_Q2",
   "messages": [
      {"role": "system", "content": "You are a concise assistant."},
      {"role": "user", "content": "Write a one-line Python function that prints hello."}
   ]
 }'
 ````

#### Test Model Summary Endpoint

In this test setup, the Model Summary Service is already enabled.  
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

You can stop one of the llama-servers and the summary endpoint will show only one model:

```bash
docker compose stop llama-server-2
curl http://127.0.0.1:8080/v1/models
docker compose start llama-server-2
```

---

## Routheon in Production

This describes a bare-metal setup without Docker. Both `traefik` and `llama.cpp` run on the same computer.

### Prerequisites

- Traefik
- llama.cpp: one or several instances of `llama-server` with dedicated ports

### Installation

#### Traefik Config: `traefik.yml`

1. Copy [`traefik.yml`](traefik/traefik.yml) to `/etc/traefik/traefik.yml`
2. Adapt the port to your needs.
3. Change logging (`accessLog`) as you like.

#### Traefik Config: Mappings API_KEY to llama.cpp instance

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

### Optional Model Summary Service

This feature requires running a small companion service that collects the `/v1/models` information from all configured
targets and provides it to Traefik.

It’s **optional** — Routheon works normally without it.
You only need it if you want `/v1/models` to list all active model servers.

The service aggregates the `/v1/models` output from all reachable `llama.cpp` servers and returns an OpenAI compatible
output as if one server was providing multiple models.

#### Installation

1. Copy [`traefik/mappings/all-models.yml`](traefik/mappings/all-models.yml) to `/etc/traefik/mappings/` (same path as
   other mappings).

2. In `all-models.yml`, change the URL to `http://127.0.0.1:9080`.

3. Copy [`traefik/all-models/all-models.py`](traefik/all-models/all-models.py) and [
   `traefik/all-models/requirements.txt`](traefik/all-models/requirements.txt) to `~/.routheon/`.

4. Create a virtual environment and install dependencies in `~/.routheon/`:
   ```bash
   python3 -m venv ~/.routheon/venv
   ~/.routheon/venv/bin/pip install -r ~/.routheon/requirements.txt
   ```

5. Set up a system daemon depending on your OS to run `all-models.py` using the virtual environment's Python.

   The daemon should run this command:
   ```bash
   ~/.routheon/venv/bin/python ~/.routheon/all-models.py
   ```

#### Customize

Adapt `all-models.py` to your setup with the following arguments:

- `--mappings`: Directory containing Traefik mapping files (default: `/etc/traefik/mappings`).
- `--host`: Host to bind the HTTP server to. Use `127.0.0.1` (default) for remote access by Traefik only.
- `--port`: Port to listen on (default: `9080`). Ensure this matches the URL in the `all-models.yml` file.
- `--skip-mapping`: YAML filenames to skip (regex patterns, default: `["all-models.yml"]`).
    - `all-models.yml`: The file for the summary itself must be in that list.
    - Add patterns for any mapping files you want to exclude from the aggregation.
- `--mapping-timeout`: Timeout in seconds for requests to each mapping (default: `2`).

Example:

```bash
~/.routheon/venv/bin/python \
 ~/.routheon/all-models.py \
   --mappings /etc/traefik/mappings \
   --host 127.0.0.1 \
   --port 9080
```

---

## License & Status

**License:** Apache License 2.0  
**Status:** Experimental / Proof of Concept
