.PHONY: start stop restart status test security-check security-audit
PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
PROFILE ?= quick

start:
	bash scripts/start.sh

stop:
	bash scripts/stop.sh

restart:
	bash scripts/restart.sh

status:
	bash scripts/status.sh

test:
	$(PYTHON) -m pytest
	$(PYTHON) -m compileall knowledge_forward tests

security-check:
	bash scripts/security_check.sh

security-audit:
	$(PYTHON) -m knowledge_forward.security_audit $(PROFILE)
