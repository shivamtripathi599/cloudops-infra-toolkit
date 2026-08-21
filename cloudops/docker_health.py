"""Docker container health inspection.

Uses the ``docker`` CLI via ``subprocess`` so no Docker SDK dependency is
required. If the ``docker`` binary is not available on ``PATH``, the toolkit
prints a clear, actionable message instead of crashing.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import List


@dataclass
class Container:
    """A Docker container (running or stopped) discovered via the CLI."""

    id: str
    name: str
    image: str
    status: str
    state: str = ""


def docker_available() -> bool:
    """Return ``True`` if the ``docker`` CLI is resolvable on ``PATH``."""
    return shutil.which("docker") is not None


def inspect_containers() -> List[Container]:
    """Return currently running containers using ``docker ps --format json``.

    Modern Docker emits one JSON object per line, which we parse directly.
    Older Docker versions without ``--format json`` are reported as an error
    so the caller can fall back to a friendly message.

    Returns:
        A list of :class:`Container` instances.

    Raises:
        RuntimeError: If docker is unavailable or the command fails.
    """
    if not docker_available():
        raise RuntimeError("docker CLI not found on PATH")

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"docker ps failed: {exc.stderr.strip()}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("docker ps timed out") from exc

    containers: List[Container] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        containers.append(
            Container(
                id=obj.get("ID", obj.get("Id", "")),
                name=obj.get("Names", obj.get("Name", "")),
                image=obj.get("Image", ""),
                status=obj.get("Status", ""),
                state=obj.get("State", ""),
            )
        )
    return containers


def render_health(containers: List[Container]) -> str:
    """Render a health table for the supplied containers."""
    if not containers:
        return "No running containers found."

    header = f"{'CONTAINER ID':<14}{'NAME':<24}{'IMAGE':<30}{'STATUS':<20}"
    rule = "-" * len(header)
    lines = [header, rule]
    for container in containers:
        lines.append(
            f"{container.id[:12]:<14}"
            f"{container.name[:23]:<24}"
            f"{container.image[:29]:<30}"
            f"{container.status[:19]:<20}"
        )
    return "\n".join(lines)
