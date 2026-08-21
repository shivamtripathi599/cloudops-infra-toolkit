"""CloudOps Infra Toolkit.

A dependency-free Python CLI for cloud/infrastructure operations:

* ``cost-report``   - grouped cloud cost summary from a JSON inventory
* ``docker-health`` - inspect running Docker containers (via the docker CLI)
* ``pod-restart``   - safe, dry-run-first Kubernetes pod remediation

The toolkit is intentionally built on the Python standard library only, so it
runs anywhere Python 3.9+ is available - no cloud credentials required.
"""

__version__ = "1.0.0"

__all__ = ["__version__"]
