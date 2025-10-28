#!/bin/bash

# Copyright (c) 2025 Stefan Kuhn.
# Licensed under Apache License 2.0.
# See: https://github.com/Wuodan/routheon

# Generate (and rotate) a Traefik mapping YAML file.
# Usage: ./create-mapping.sh --port <port> --service <service> --api_key <api_key> [--mappings <mappings>] [--host <host>]
# Example: ./create-mapping.sh --port 8011 --service llama-server-1 --api_key API_KEY-1 --mappings /etc/traefik/mappings --host http://127.0.0.1

set -euo pipefail

function usage() {
    echo "Usage: $0 --port <port> --service <service> --api_key <api_key> [--mappings <mappings>] [--host <host>]"
    echo "Generate a Traefik mapping YAML file."
    echo
    echo "Arguments:"
    echo "  --port      Port number of target"
    echo "  --service   Traefik service name"
    echo "  --api_key   API key for routing"
    echo "  --mappings  Directory to output the mapping file (default: /etc/traefik/mappings)"
    echo "  --host      Target host (default: http://127.0.0.1)"
    exit 1
}

PORT=""
SERVICE=""
API_KEY=""
MAPPINGS="/etc/traefik/mappings"
HOST="http://127.0.0.1"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --port) PORT="$2"; shift ;;
        --service) SERVICE="$2"; shift ;;
        --api_key) API_KEY="$2"; shift ;;
        --mappings) MAPPINGS="$2"; shift ;;
        --host) HOST="$2"; shift ;;
        --help) usage ;;
        *) echo "Unknown parameter passed: $1"; usage ;;
    esac
    shift
done

if [ -z "$PORT" ] || [ -z "$SERVICE" ] || [ -z "$API_KEY" ]; then
    echo "Error: --port, --service, and --api_key are required."
    usage
fi

# Convert illegal chars in service name to underscore (in case raw HF model is passed)
SERVICE="$(printf '%s' "$SERVICE" | sed 's/[^A-Za-z0-9._-]/_/g')"

echo "Creating mapping file '$MAPPINGS/${SERVICE}.yml' for Traefik service '$SERVICE' on '$HOST:$PORT'"

if [ ! -d "$MAPPINGS" ]; then
    >&2 echo "Error: Mapping directory does not exist at $MAPPINGS"
    exit 1
fi

# Rotate old mappings that use the same API key
# - only .yml / .yaml
# - skip the file we're about to create (${SERVICE}.yml)
timestamp="$(date +%Y%m%d-%H%M%S)"
MATCHED_FILES="$(
    grep -rl \
        --include="*.yml" \
        --include="*.yaml" \
        --exclude="${SERVICE}.yml" \
        "\^Bearer ${API_KEY}\\$" "$MAPPINGS" || true
        # need '\\$' in above regex !!
)"
if [ -n "$MATCHED_FILES" ]; then
    echo "Rotating these other mapping files with same API_KEY:"
    echo "$MATCHED_FILES"
    echo "$MATCHED_FILES" | while IFS= read -r match_file; do
        new_name="${match_file}.bak.${timestamp}"
        mv "$match_file" "$new_name"
        echo "Rotated $match_file -> $new_name"
    done
    echo "Done rotating"
else
    echo "Good - API_KEY not found in any other mapping files."
fi

TEMPLATE="http:
  routers:
    ${SERVICE}:
      rule: \"HeaderRegexp(\`Authorization\`, \`^Bearer ${API_KEY}$\`)\"
      service: ${SERVICE}
      entryPoints:
        - llama-servers

  services:
    ${SERVICE}:
      loadBalancer:
        servers:
          - url: \"${HOST}:${PORT}\""

# Ensure output directory exists
mkdir -p "$MAPPINGS"

# Write to file
OUTPUT_PATH="${MAPPINGS}/${SERVICE}.yml"
echo "$TEMPLATE" > "$OUTPUT_PATH"

echo "Generated mapping file: $OUTPUT_PATH"
