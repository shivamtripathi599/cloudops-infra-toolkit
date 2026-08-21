# ☁️ cloudops-infra-toolkit

A **dependency-free** Python CLI toolkit for everyday **CloudOps / SRE**
operations: cloud cost reporting, Docker container health, and safe Kubernetes
pod remediation.

Designed so it runs **without any cloud credentials** — Docker and Kubernetes
commands are real when their CLIs are present, but degrade gracefully to a clear
message (or a safe **dry-run plan**) when they aren't. This makes it ideal for
demos, interviews, CI, and learning the *shape* of CloudOps automation.

---

## ✨ Features

- 💰 **`cost-report`** — group a JSON resource inventory by `(type, region)`,
  sum monthly spend, and print a tidy table + grand total.
- 🐳 **`docker-health`** — inspect running containers via the `docker` CLI
  (no Docker SDK needed); prints a clear message if Docker isn't available.
- ♻️ **`pod-restart`** — plan (and optionally apply) rollout restarts for
  unhealthy pods. **Dry-run by default** — safe-by-design, auditable
  remediation.
- 📦 **Zero runtime dependencies** — pure Python standard library.
- 🧪 **Tested + CI-ready** — `pytest` suite + GitHub Actions workflow.
- 🐳 **Dockerised** — run the toolkit from a slim image.

---

## 🏗️ Commands

```
cloudops
├── cost-report   --inventory inv.json        # grouped cloud spend summary
├── docker-health                              # running-container health table
└── pod-restart    --namespace default         # k8s remediation (DRY-RUN by default)
                 [--no-dry-run]                #   apply (needs a live cluster)
```

---

## 📦 Installation

No third-party packages required at runtime.

```bash
git clone https://github.com/shivamtripathi599/cloudops-infra-toolkit.git
cd cloudops-infra-toolkit
pip install -e .            # installs the `cloudops` command (optional)
pip install pytest          # only needed to run tests
```

---

## ▶️ Usage

### Cost report

```bash
python -m cloudops cost-report --inventory examples/inventory.json
```

```
Cost report for examples/inventory.json

TYPE          REGION         COUNT    MONTHLY_COST
--------------------------------------------------
ec2           us-east-1          2          326.95
rds           us-east-1          1          312.50
rds           eu-west-1          1          205.10
eks           us-east-1          1          146.00
ec2           eu-west-1          1           96.40
cloudfront    global             1           78.90
s3            us-east-1          1           23.15
s3            eu-west-1          1           11.80
lambda        us-east-1          1            4.30
--------------------------------------------------
TOTAL                           10         1205.10
```

### Docker health

```bash
python -m cloudops docker-health
```

Shows a container table, or `docker CLI not found on PATH.` if Docker isn't
installed.

### Pod remediation (dry-run first 🔒)

```bash
python -m cloudops pod-restart --dry-run
```

```
Kubernetes pod remediation :: namespace=default :: DRY-RUN (no changes will be made)

Planned actions (2):
  - kubectl rollout restart deployment/api-gateway -n default
      reason: pod in unhealthy state 'CrashLoopBackOff' (restarts=14)
  - kubectl rollout restart deployment/worker -n default
      reason: pod in unhealthy state 'ImagePullBackOff' (restarts=3)

Dry-run complete. Re-run with --no-dry-run to apply (requires a configured kubecontext).
```

When a live, credentialed cluster is reachable and you pass `--no-dry-run`, the
planned `kubectl rollout restart` commands are actually executed.

---

## 🐳 Docker

```bash
docker build -t cloudops .
docker run --rm cloudops cost-report --inventory examples/inventory.json
```

---

## 🧪 Testing

```bash
pytest -q
```

The suite covers cost aggregation, the remediation planner (healthy/unhealthy
filtering, namespace scoping, workload-name stripping), and the demo sample.

---

## 🔧 Tech stack

`Python` (stdlib only) · `Docker CLI` · `kubectl` · `pytest` ·
`Docker` · `GitHub Actions`

---

> 💡 *Pairs well with
> [aiops-log-anomaly-detector](https://github.com/shivamtripathi599/aiops-log-anomaly-detector):
> detect the anomaly there, remediate the failing pod here.*
