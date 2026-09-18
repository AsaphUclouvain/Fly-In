.PHONY: install run debug clean fclean lint lint-strict test

PYTHON      ?= python3
VENV        ?= .venv
VENV_PYTHON := $(VENV)/bin/python
MAP         ?= maps/easy/02_simple_fork.txt
OUTPUT      ?= sim_output.txt

install: $(VENV_PYTHON)
	$(VENV_PYTHON) -m pip install -r requirements-dev.txt

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

run:
	$(VENV_PYTHON) -m fly_in.main $(MAP) -o $(OUTPUT)

debug:
	$(VENV_PYTHON) -m pdb -m fly_in.main $(MAP) -o $(OUTPUT)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

fclean: clean
	rm -rf sim_output.txt

lint:
	$(VENV_PYTHON) -m flake8 .
	$(VENV_PYTHON) -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs

lint-strict:
	$(VENV_PYTHON) -m flake8 .
	$(VENV_PYTHON) -m mypy . --strict

test:
	$(VENV_PYTHON) -m pytest -q
