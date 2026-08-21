.PHONY: install test run-cost run-pods docker-health

install:
	pip install -e . pytest

test:
	pytest -q

run-cost:
	python -m cloudops cost-report --inventory examples/inventory.json

run-pods:
	python -m cloudops pod-restart --dry-run

docker-health:
	python -m cloudops docker-health
