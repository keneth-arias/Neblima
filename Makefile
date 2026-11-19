.PHONY: setup init check test test-timef-offline build audit doctor

setup:
	uv sync --locked

init:
	uv run --locked airaware workspace init

check:
	uv lock --check
	uv run --locked ruff format --check src tests tools/training
	uv run --locked ruff check src tests tools/training
	uv run --locked ty check src tests
	uv run --locked airaware catalog validate
	uv run --locked pytest

test:
	uv run --locked pytest

test-timef-offline:
	UV_OFFLINE=true uv run --locked ruff check tools/timenet-smoke
	UV_OFFLINE=true uv run --locked ruff format --check tools/timenet-smoke
	UV_OFFLINE=true /usr/bin/time -f 'Tiempo=%e s Memoria residente máxima=%M KiB' uv run --project tools/timenet-smoke --locked python -m unittest discover -s tools/timenet-smoke -p 'test_*.py'

build:
	uv build

audit:
	uv run --locked pip-audit --local --skip-editable

doctor:
	uv run --locked airaware doctor
