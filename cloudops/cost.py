"""Cost-reporting logic for the CloudOps toolkit.

Reads a JSON inventory of cloud resources and produces a grouped cost summary.
The aggregation logic is intentionally pure and side-effect free so it can be
unit-tested without touching the filesystem or any cloud provider.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class Resource:
    """A single billable cloud resource."""

    name: str
    type: str
    region: str
    monthly_cost: float


@dataclass
class GroupSummary:
    """Aggregated cost for one ``(type, region)`` bucket."""

    type: str
    region: str
    count: int = 0
    total_cost: float = 0.0


def load_inventory(path: str | Path) -> List[Resource]:
    """Load and validate a resource inventory from a JSON file.

    The JSON must be a list of objects, each with ``type``, ``region`` and
    ``monthly_cost`` keys (``name`` is optional and defaults to an index).

    Args:
        path: Filesystem path to the inventory JSON file.

    Returns:
        A list of :class:`Resource` instances.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON is malformed or a resource is missing fields.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Inventory file not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(raw, list):
        raise ValueError("Inventory JSON must be a list of resource objects.")

    resources: List[Resource] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Resource #{idx} must be a JSON object.")
        try:
            resources.append(
                Resource(
                    name=str(item.get("name", f"resource-{idx}")),
                    type=str(item["type"]),
                    region=str(item["region"]),
                    monthly_cost=float(item["monthly_cost"]),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Resource #{idx} is malformed: {exc}") from exc
    return resources


def aggregate_costs(resources: List[Resource]) -> Dict[Tuple[str, str], GroupSummary]:
    """Group resources by ``(type, region)`` and sum their monthly cost.

    Args:
        resources: The resources to aggregate.

    Returns:
        A mapping of ``(type, region)`` -> :class:`GroupSummary`.
    """
    groups: Dict[Tuple[str, str], GroupSummary] = {}
    for res in resources:
        key = (res.type, res.region)
        summary = groups.get(key)
        if summary is None:
            summary = GroupSummary(type=res.type, region=res.region)
            groups[key] = summary
        summary.count += 1
        summary.total_cost += res.monthly_cost
    return groups


def render_report(resources: List[Resource]) -> str:
    """Render a grouped cost summary table plus a grand total as a string.

    The rows are sorted by total monthly cost (descending) for readability.
    """
    groups = aggregate_costs(resources)
    ordered = sorted(groups.values(), key=lambda g: g.total_cost, reverse=True)

    header = f"{'TYPE':<14}{'REGION':<14}{'COUNT':>6}{'MONTHLY_COST':>16}"
    rule = "-" * len(header)
    lines: List[str] = [header, rule]

    grand_total = 0.0
    for group in ordered:
        grand_total += group.total_cost
        lines.append(
            f"{group.type:<14}{group.region:<14}{group.count:>6}"
            f"{group.total_cost:>16.2f}"
        )
    lines.append(rule)
    lines.append(
        f"{'TOTAL':<14}{'':<14}{len(resources):>6}{grand_total:>16.2f}"
    )
    return "\n".join(lines)
