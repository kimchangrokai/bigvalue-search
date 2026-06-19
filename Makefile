.PHONY: install install-dev lint format test clean run

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	playwright install chromium

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

test:
	pytest tests/

test-cov:
	pytest tests/ --cov=bigvalue_search --cov-report=html

run:
	python -m bigvalue_search --address "서울 강서구 마곡동 800-15" --radius 50 --output both

clean:
	powershell -Command "Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist, *.egg-info, .pytest_cache, .mypy_cache, htmlcov, .coverage"
	powershell -Command "Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
