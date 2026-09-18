.PHONY: install run debug clean lint lint-strict test

PYTHON  ?= python3
MAP     ?= maps/easy/02_simple_fork.txt
OUTPUT  ?= sim_output.txt

install:
	$(PYTHON) -m pip install --break-system-packages -r requirements-dev.txt

run:
	$(PYTHON) -m fly_in.main $(MAP) -o $(OUTPUT)

debug:
	$(PYTHON) -m pdb -m fly_in.main $(MAP) -o $(OUTPUT)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

fclean: clean
	rm -rf sim_output.txt

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports \
		--disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict

test:
	pytest -q
