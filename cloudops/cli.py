"""Command-line interface for the CloudOps Infra Toolkit.

Exposes three subcommands through :mod:`argparse`:

* ``cost-report``   - grouped cloud cost summary from a JSON inventory
* ``docker-health`` - inspect running Docker containers
* ``pod-restart``   - safe, dry-run-first Kubernetes pod remediation

Every command is designed to run WITHOUT cloud credentials. Docker and
Kubernetes commands are real when their CLIs are present, but degrade to a
clear message (or a dry-run plan) when they are not.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from cloudops import __version__
from cloudops import cost as cost_mod
from cloudops import docker_health as docker_mod
from cloudops import k8s as k8s_mod


def _build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser and its subparsers."""
    parser = argparse.ArgumentParser(
        prog="cloudops",
        description="CloudOps Infra Toolkit - cost, containers, and k8s remediation.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"cloudops {__version__}",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # cost-report ------------------------------------------------------------
    p_cost = sub.add_parser(
        "cost-report",
        help="Print a grouped cost summary from a JSON inventory.",
    )
    p_cost.add_argument(
        "--inventory",
        required=True,
        help="Path to a JSON inventory file (list of resource objects).",
    )

    # docker-health ----------------------------------------------------------
    sub.add_parser(
        "docker-health",
        help="Inspect running Docker containers (via the docker CLI).",
    )

    # pod-restart ------------------------------------------------------------
    p_pod = sub.add_parser(
        "pod-restart",
        help="Plan/restart unhealthy Kubernetes pods (dry-run by default).",
    )
    p_pod.add_argument(
        "--namespace",
        default="default",
        help="Kubernetes namespace to scan (default: default).",
    )
    p_pod.add_argument(
        "--dry-run",
        dest="dry_run",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Plan actions without executing (default: on). Use --no-dry-run to apply.",
    )

    return parser


def cmd_cost_report(args: argparse.Namespace) -> int:
    """Run the ``cost-report`` subcommand."""
    try:
        resources = cost_mod.load_inventory(args.inventory)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not resources:
        print("Inventory is empty - nothing to report.")
        return 0

    print(f"Cost report for {args.inventory}\n")
    print(cost_mod.render_report(resources))
    return 0


def cmd_docker_health(_args: argparse.Namespace) -> int:
    """Run the ``docker-health`` subcommand."""
    if not docker_mod.docker_available():
        print(
            "docker CLI not found on PATH.\n"
            "Install Docker Desktop or add docker to PATH to inspect containers."
        )
        return 0

    try:
        containers = docker_mod.inspect_containers()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(docker_mod.render_health(containers))
    return 0


def cmd_pod_restart(args: argparse.Namespace) -> int:
    """Run the ``pod-restart`` subcommand (dry-run by default)."""
    namespace: str = args.namespace
    dry_run: bool = args.dry_run

    # Mode banner - clarifies the safety posture of the run.
    mode = "DRY-RUN (no changes will be made)" if dry_run else "APPLY (live changes)"
    print(f"Kubernetes pod remediation :: namespace={namespace} :: {mode}\n")

    # In dry-run, or when kubectl is unavailable / the cluster is unreachable,
    # fall back to a DEMO plan so the remediation design is always demonstrable
    # without a live, credentialed cluster.
    if dry_run or not k8s_mod.kubectl_available():
        if not k8s_mod.kubectl_available():
            print("kubectl CLI not found on PATH - showing a DEMO plan with sample pods.\n")
            pods = k8s_mod.DemoSample().pods
        else:
            try:
                pods = k8s_mod.discover_pods(namespace)
            except RuntimeError as exc:
                print(f"Could not reach the cluster ({exc}); showing a DEMO plan.\n")
                pods = k8s_mod.DemoSample().pods
    else:
        # Live apply path - require a working cluster.
        try:
            pods = k8s_mod.discover_pods(namespace)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    actions = k8s_mod.plan_remediation(pods, namespace)
    if not actions:
        print(f"No unhealthy pods found in namespace '{namespace}'.")
        return 0

    print(f"Planned actions ({len(actions)}):")
    for action in actions:
        print(f"  - {action.description}")
        print(f"      reason: {action.reason}")

    if dry_run:
        print(
            "\nDry-run complete. Re-run with --no-dry-run to apply "
            "(requires a configured kubecontext)."
        )
        return 0

    # Live apply path (only reached when --no-dry-run and kubectl present).
    outputs = k8s_mod.execute_remediation(actions)
    print("\nResults:")
    for line in outputs:
        print(f"  {line}")
    return 0


_COMMANDS = {
    "cost-report": cmd_cost_report,
    "docker-health": cmd_docker_health,
    "pod-restart": cmd_pod_restart,
}


def main(argv: Optional[List[str]] = None) -> int:
    """Parse arguments and dispatch to the chosen subcommand.

    Returns:
        A process exit code (0 = success).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _COMMANDS[args.command]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
