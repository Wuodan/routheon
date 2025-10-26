# Routheon

Lightweight API_KEY router compatible with the OpenAI protocol.  
Route multiple `llama.cpp` model servers through a single API endpoint using Traefik.

---

## Overview

Routheon acts as a reverse proxy that exposes one unified API endpoint (compatible with `/v1/chat/completions`) and routes incoming API requests to different `llama.cpp` model servers based on the provided API key.

This enables per-user or per-model access control while keeping the architecture simple.

---

## Architecture

```text
           ┌─────────────────────┐
           │    Traefik Router   │
           │ (port 8080, /v1/..) │
           └─────────┬───────────┘
                     │
     ┌───────────────┴────────────────┐
     │                                │
┌────────────────┐           ┌────────────────┐
│ llama-server-1 │           │ llama-server-2 │
│ TinyLlama_Q2   │           │ Mistral-tiny_Q2│
└────────────────┘           └────────────────┘
 (API_KEY-1 → server-1)       (API_KEY-2 → server-2)
```

---

## Routheon Test

The Routheon test sets up an API_KEY router using [Traefik](https://doc.traefik.io/traefik/) and includes two [llama.cpp](https://github.com/ggml-org/llama.cpp) servers with small models.

### Prerequisites

- Docker Compose

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

Wait for all `llama-server` services to be `healthy`. The models must be downloaded before the services are fully operational.

To check status, run:
```bash
docker compose ps
```

#### Clean-up after Test

The models are stored in a Docker volume. When you are done testing, delete images and the volume with:

```bash
docker compose down
docker image rm traefik:latest ghcr.io/ggml-org/llama.cpp:server python:slim
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
```

---

## Routheon in Production

This describes a bare-metal setup without Docker. Both `traefik` and `llama.cpp` run on the same computer.

### Prerequisites

- Traefik
- llama.cpp: one or several instances of `llama-server` with dedicated ports

### Installation

#### Traefik Config: `traefik.yml`

Copy [`traefik.yml`](traefik/traefik.yml) to `/etc/traefik/traefik.yml`  
Adapt the port to your needs.

#### Traefik Config: Mappings API_KEY to llama.cpp instance

- Create mappings in `/etc/traefik/mappings/`
- For each `llama.cpp` instance, create a `my-server.yml` file like [llama-server-1.yml](traefik/mappings/llama-server-1.yml)
- The `url` must be `http://127.0.0.1:<LLAMA_PORT>`

#### Traefik Service

- Configure a system daemon for Traefik depending on your OS
- The path of the mappings folder can be changed in `traefik.yml`
- If you choose another path for `traefik.yml`, use the `traefik --configFile <PATH>` parameter

### llama.cpp

Run `llama-server` without the `--host` parameter (so it defaults to `127.0.0.1`) to prevent direct remote access to its port.

### Ready to Use

- All instances of `llama.cpp` can now be accessed remotely via a single common port
- Access to each instance is controlled by API_KEY

---

## Use Cases

- Run multiple `llama.cpp` instances behind a single API
- Provide per-user or per-model access via API keys
- Simplify client integration using an OpenAI-compatible endpoint

---

## License & Status

**License:** Apache License 2.0
**Status:** Experimental / Proof of Concept
