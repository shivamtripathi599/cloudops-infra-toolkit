"""Safe Kubernetes pod remediation (dry-run first).

The remediation *planner* is a pure function so it can be unit-tested without
``kubectl``. In the real CLI, unhealthy pods are discovered with
``kubectl get pods -o json``; when ``kubectl`` is unavailable (or in dry-run),
the toolkit prints the plan without executing anything - demonstrating the
safe, auditable remediation design expected in a CloudOps/SRE workflow.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List


# Pod phases / container states we consider unhealthy and worth remediating.
UNHEALTHY_STATES = {
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "Error",
    "Failed",
    "Unknown",
}

# Default kubectl binary name used when building remediation commands.
DEFAULT_KUBECTL = "kubectl"


@dataclass
class Pod:
    """A Kubernetes pod summary used by the planner."""

    name: str
    namespace: str
    status: str
    restarts: int = 0


@dataclass
class RemediationAction:
    """A single planned (or executed) remediation step."""

    namespace: str
    pod: str
    command: List[str]
    reason: str

    @property
    def description(self) -> str:
        """Human-readable rendering of the command to be run."""
        return " ".join(self.command)


@dataclass
class DemoSample:
    """Curated example pods used to illustrate the plan when kubectl is absent.

    This lets the dry-run planner show realistic output without a live cluster
    and without any credentials.
    """

    pods: List[Pod] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.pods = [
            Pod("api-gateway-7d9f", "default", "CrashLoopBackOff", 14),
            Pod("worker-5c2b", "default", "ImagePullBackOff", 3),
            Pod("cache-redis-0", "default", "Running", 0),
            Pod("frontend-9a1c", "kube-system", "Error", 7),
        ]


def _workload_name(pod_name: str) -> str:
    """Strip the trailing replica/hash suffix from a pod name.

    ``api-gateway-7d9f`` -> ``api-gateway``; ``cache-redis-0`` -> ``cache-redis``.
    Names without a trailing alphanumeric token are returned unchanged.
    """
    parts = pod_name.rsplit("-", 1)
    if len(parts) == 2 and parts[1].isalnum():
        return parts[0]
    return pod_name


def is_unhealthy(pod: Pod) -> bool:
    """Return ``True`` if a pod's status indicates it needs remediation."""
    return pod.status in UNHEALTHY_STATES


def plan_remediation(
    pods: List[Pod],
    namespace: str,
    kubectl: str = DEFAULT_KUBECTL,
) -> List[RemediationAction]:
    """Build a remediation plan for unhealthy pods in a namespace.

    Pure function: given a list of pods, return the restart actions that would
    be taken. Pods outside ``namespace`` are ignored.

    Args:
        pods: Candidate pods (real or demo).
        namespace: Only pods in this namespace are considered.
        kubectl: kubectl binary name used when constructing commands.

    Returns:
        A list of :class:`RemediationAction` (empty if nothing to do).
    """
    actions: List[RemediationAction] = []
    for pod in pods:
        if pod.namespace != namespace:
            continue
        if not is_unhealthy(pod):
            continue
        workload = _workload_name(pod.name)
        actions.append(
            RemediationAction(
                namespace=namespace,
                pod=pod.name,
                command=[
                    kubectl,
                    "rollout",
                    "restart",
                    f"deployment/{workload}",
                    "-n",
                    namespace,
                ],
                reason=(
                    f"pod in unhealthy state '{pod.status}' "
                    f"(restarts={pod.restarts})"
                ),
            )
        )
    return actions


def kubectl_available() -> bool:
    """Return ``True`` if the ``kubectl`` CLI is resolvable on ``PATH``."""
    return shutil.which(DEFAULT_KUBECTL) is not None


def discover_pods(namespace: str, kubectl: str = DEFAULT_KUBECTL) -> List[Pod]:
    """Query ``kubectl`` for pods in a namespace (real discovery).

    Raises:
        RuntimeError: If kubectl is unavailable or the command fails.
    """
    if not kubectl_available():
        raise RuntimeError("kubectl CLI not found on PATH")

    try:
        result = subprocess.run(
            [kubectl, "get", "pods", "-n", namespace, "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"kubectl get pods failed: {exc.stderr.strip()}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("kubectl get pods timed out") from exc

    data = json.loads(result.stdout)
    pods: List[Pod] = []
    for item in data.get("items", []):
        meta = item.get("metadata", {})
        status = item.get("status", {})
        pod_status = status.get("phase", "")
        restarts = 0
        detailed = ""
        for cs in status.get("containerStatuses", []) or []:
            restarts = max(restarts, cs.get("restartCount", 0))
            for state_name, state_body in cs.get("state", {}).items():
                if state_name in ("waiting", "terminated"):
                    reason = state_body.get("reason", "")
                    if reason:
                        detailed = reason
        pods.append(
            Pod(
                name=meta.get("name", "?"),
                namespace=meta.get("namespace", namespace),
                status=detailed or pod_status,
                restarts=restarts,
            )
        )
    return pods


def execute_remediation(
    actions: List[RemediationAction],
    kubectl: str = DEFAULT_KUBECTL,
) -> List[str]:
    """Actually run the remediation actions via kubectl.

    Args:
        actions: The actions produced by :func:`plan_remediation`.

    Returns:
        One output line per action (stdout on success, an ERROR line on failure).

    Raises:
        RuntimeError: If kubectl is not available.
    """
    if not kubectl_available():
        raise RuntimeError("kubectl CLI not found on PATH")

    outputs: List[str] = []
    for action in actions:
        try:
            result = subprocess.run(
                action.command,
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            outputs.append(result.stdout.strip() or "restart triggered")
        except subprocess.CalledProcessError as exc:
            outputs.append(f"ERROR: {exc.stderr.strip()}")
    return outputs
