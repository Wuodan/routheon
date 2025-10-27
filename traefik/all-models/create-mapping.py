#!/usr/bin/env python3

"""
Copyright (c) 2025 Stefan Kuhn.

Licensed under Apache License 2.0.
See: https://github.com/Wuodan/routheon
"""

import argparse
import os

TEMPLATE = """http:
  routers:
    {SERVICE}:
      rule: "HeaderRegexp(`Authorization`, `^Bearer ({API_KEY})$`)"
      service: {SERVICE}
      entryPoints:
        - llama-servers

  services:
    {SERVICE}:
      loadBalancer:
        servers:
          - url: "{HOST}:{PORT}"
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Traefik mapping YAML file.")
    parser.add_argument("port",
                        type=int,
                        help="Port number to replace 8011")
    parser.add_argument("service",
                        help="Service name to replace llama-server-1")
    parser.add_argument("api_key",
                        help="API key string to replace API_KEY-1")
    parser.add_argument("--mappings",
                        default="/etc/traefik/mappings",
                        help="Directory to output the mapping file")
    parser.add_argument("--host",
                        default="http://127.0.0.1",
                        help="Host of the llama-server service")
    args = parser.parse_args()

    # Perform replacements
    content = TEMPLATE.format(
        SERVICE=args.service,
        API_KEY=args.api_key,
        PORT=args.port,
        HOST=args.host
    )

    # Ensure output directory exists
    os.makedirs(args.mappings, exist_ok=True)

    # Write to file
    output_path = os.path.join(args.mappings, f"{args.service}.yml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Generated mapping file: {output_path}")


if __name__ == "__main__":
    main()
