"""Tests for traefik/create-mapping/create-mapping.sh."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
SCRIPT_PATH: Path = REPO_ROOT / "traefik" / "create-mapping" / "create-mapping.sh"


def _run_script(args: List[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Execute the shell script with the given arguments."""

    command: List[str] = ["bash", str(SCRIPT_PATH), *args]
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_create_mapping_requires_arguments(tmp_path: Path) -> None:
    """Script should fail when mandatory arguments are missing."""

    result = _run_script(
        ["--service", "svc", "--api_key", "API_KEY-1", "--mappings", str(tmp_path)],
        cwd=tmp_path,
    )
    assert result.returncode != 0
    assert "Usage:" in result.stdout


def test_create_mapping_generates_and_rotates(tmp_path: Path) -> None:
    """Script should generate mapping file and rotate previous matches."""

    mappings_dir: Path = tmp_path / "mappings"
    mappings_dir.mkdir()

    legacy_file: Path = mappings_dir / "old.yml"
    legacy_file.write_text(
        """http:
  routers:
    old:
      rule: "HeaderRegexp(`Authorization`, `^Bearer API_KEY-1$`)"
""",
        encoding="utf-8",
    )

    result = _run_script(
        [
            "--port",
            "8011",
            "--service",
            "new service",
            "--api_key",
            "API_KEY-1",
            "--mappings",
            str(mappings_dir),
            "--host",
            "http://127.0.0.1",
        ],
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr

    generated_file: Path = mappings_dir / "new_service.yml"
    assert generated_file.exists()
    contents: str = generated_file.read_text(encoding="utf-8")
    assert 'service: new_service' in contents
    assert 'url: "http://127.0.0.1:8011"' in contents

    backups: List[Path] = list(mappings_dir.glob("old.yml.bak.*"))
    assert backups, "Expected rotated backup file to exist"
