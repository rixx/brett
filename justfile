default:
    @just --list

# Install dependencies (use --extras to include e.g. dev)
[group('development')]
install *args:
    uv sync {{ args }}

# Install all dependencies
[group('development')]
install-all:
    uv sync --all-extras

# Run the development server or other commands, e.g. `just run makemigrations`
[group('development')]
[working-directory("src")]
run *args="runserver":
    uv run python manage.py {{ args }}

# Open Django shell
[group('development')]
[working-directory("src")]
shell *args:
    just run shell {{ args }}

# Clean up generated files
[group('development')]
clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    rm -rf .pytest_cache
    rm -rf .coverage htmlcov
    rm -rf dist build

# Run the test suite
[group('tests')]
test *args:
    uv run pytest -p no:doctest -p no:pastebin -p no:nose {{ args }}

# Run tests with coverage report
[group('tests')]
test-coverage *args:
    just test --cov=src/ --cov-report=term-missing {{ args }}

# Format code with black
[group('linting')]
black *args:
    uv run black src {{ args }}

# Check code with black (check only)
[group('linting')]
black-check:
    uv run black --check src

# Sort imports with isort
[group('linting')]
isort *args:
    uv run isort src {{ args }}

# Check import sorting with isort (check only)
[group('linting')]
isort-check:
    uv run isort --check src

# Run flake8 linter
[group('linting')]
flake8 *args:
    uv run flake8 src {{ args }}

# Format code with black and isort
[group('linting')]
fmt: black isort flake8

# Check code quality
[group('linting')]
check: black-check isort-check flake8

# Run migrations
[group('development')]
[working-directory("src")]
migrate:
    just run migrate

# Create migrations
[group('development')]
[working-directory("src")]
makemigrations *args:
    just run makemigrations {{ args }}
