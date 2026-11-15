.PHONY: setup init check test build audit doctor

setup:
	uv sync --locked

init:
	uv run --locked airaware workspace init

check:
	uv lock --check
	uv run --locked ruff format --check src tests
	uv run --locked ruff check src tests
	uv run --locked ty check src tests
	uv run --locked airaware catalog validate
	uv run --locked pytest

test:
	uv run --locked pytest

build:
	uv build

audit:
	uv run --locked pip-audit --local --skip-editable

doctor:
	uv run --locked airaware doctor
