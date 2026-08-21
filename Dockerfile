FROM python:3.11-slim

WORKDIR /app

# Install the toolkit (stdlib-only at runtime).
COPY requirements.txt /app/requirements.txt
COPY setup.py pyproject.toml /app/
COPY cloudops /app/cloudops
COPY examples /app/examples

RUN pip install --no-cache-dir /app

# Defaults to a safe, credential-free dry-run plan.
ENTRYPOINT ["python", "-m", "cloudops"]
CMD ["pod-restart", "--dry-run"]
