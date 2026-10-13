.PHONY: setup backend frontend test check clean
ifeq ($(OS),Windows_NT)
    NPM ?= npm.cmd
    ifeq ($(wildcard backend/.venv/Scripts/python.exe),backend/.venv/Scripts/python.exe)
        PYTHON ?= backend/.venv/Scripts/python.exe
    else
        PYTHON ?= python
    endif
else
    NPM ?= npm
    ifeq ($(wildcard backend/.venv/bin/python),backend/.venv/bin/python)
        PYTHON ?= backend/.venv/bin/python
    else
        PYTHON ?= python3
    endif
endif

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r backend/requirements.txt
	$(PYTHON) -m playwright install chromium
	cd frontend && $(NPM) install

backend:
	$(PYTHON) -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload --loop backend.app.loops:event_loop_factory

frontend:
	cd frontend && $(NPM) run dev

test:
	$(PYTHON) -m pytest backend/tests/ -v
	cd frontend && $(NPM) test -- --run

check:
	$(PYTHON) -m ruff check backend/
	$(PYTHON) -m pytest backend/tests/ -v
	cd frontend && $(NPM) run typecheck
	cd frontend && $(NPM) test -- --run
	cd frontend && $(NPM) run build
	$(PYTHON) scripts/security_scan.py

security:
	$(PYTHON) scripts/security_scan.py

clean:
	rm -rf backend/__pycache__ backend/*/__pycache__ backend/data/*.db frontend/dist frontend/node_modules
