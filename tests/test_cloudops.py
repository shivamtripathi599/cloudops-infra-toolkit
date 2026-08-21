"""Unit tests for the CloudOps Infra Toolkit (pure, no external CLIs)."""

from __future__ import annotations

from pathlib import Path

from cloudops import cost, k8s


def test_load_inventory_and_aggregate():
    inv = Path(__file__).resolve().parent.parent / "examples" / "inventory.json"
    resources = cost.load_inventory(inv)
    assert len(resources) == 10
    groups = cost.aggregate_costs(resources)
    # Two ec2 resources in us-east-1 should be merged into one group.
    assert groups[("ec2", "us-east-1")].count == 2
    # Sum of the two us-east-1 ec2 costs.
    assert groups[("ec2", "us-east-1")].total_cost == 184.20 + 142.75


def test_render_report_total():
    resources = cost.load_inventory(
        Path(__file__).resolve().parent.parent / "examples" / "inventory.json"
    )
    report = cost.render_report(resources)
    assert "TOTAL" in report
    # Grand total of all 10 resources.
    expected = 184.20 + 142.75 + 96.40 + 312.50 + 205.10 + 78.90 + 23.15 + 11.80 + 4.30 + 146.00
    assert f"{expected:.2f}" in report


def test_plan_remediation_finds_unhealthy():
    pods = [
        k8s.Pod("api-gateway-7d9f", "default", "CrashLoopBackOff", 14),
        k8s.Pod("cache-redis-0", "default", "Running", 0),
        k8s.Pod("frontend-9a1c", "kube-system", "Error", 7),
    ]
    actions = k8s.plan_remediation(pods, namespace="default")
    # Only the default-namespace unhealthy pod is planned.
    assert len(actions) == 1
    assert actions[0].pod == "api-gateway-7d9f"
    assert actions[0].command[0] == "kubectl"
    assert "rollout" in actions[0].command
    assert "default" in actions[0].command


def test_plan_remediation_ignores_healthy_and_other_ns():
    pods = [
        k8s.Pod("cache-redis-0", "default", "Running", 0),
        k8s.Pod("frontend-9a1c", "kube-system", "Error", 7),
    ]
    actions = k8s.plan_remediation(pods, namespace="default")
    assert actions == []


def test_demo_sample_has_unhealthy_pods():
    pods = k8s.DemoSample().pods
    unhealthy = [p for p in pods if k8s.is_unhealthy(p)]
    assert len(unhealthy) >= 2


def test_workload_name_strips_suffix():
    assert k8s._workload_name("api-gateway-7d9f") == "api-gateway"
    assert k8s._workload_name("cache-redis-0") == "cache-redis"
    assert k8s._workload_name("standalone") == "standalone"
