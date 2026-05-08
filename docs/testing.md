# Testing

`python_magnetapi` includes a test suite that exercises the API interaction
layer against a running MagnetDB instance.

## Prerequisites

Tests require:

1. A running MagnetDB instance
2. A valid API key exported as `MAGNETDB_API_KEY`
3. Development dependencies installed:

```bash
pip install -e ".[dev]"
```

## Running Tests

```bash
export MAGNETDB_API_KEY=your_api_key_here

# Run all tests
pytest

# Run with verbose output
pytest --verbose

# Run a specific test file
pytest tests/test_list.py

# Run a specific test class or method
pytest tests/test_list.py::TestList::test_material

# Run with coverage
pytest --cov=python_magnetapi --cov-report=html --cov-report=term
```

## Testing Inside Docker

When testing against a local MagnetDB instance running in Docker:

```bash
export MAGNETDB_API_KEY=test
export MAGNETDB_API_SERVER=http://localhost:8000
pytest --verbose
```

## Test Structure

```text
tests/
├── __init__.py
└── test_list.py        # List, CRUD, and integration tests
```

The test suite covers:

- **TestList**: Verifies that listing each object type returns results
  (materials, parts, magnets, sites, records, simulations).
- **TestCrud**: Tests create, read, update, and delete operations for each
  object type using sample data files.

## Writing New Tests

Create test files following the `test_*.py` naming convention in the
`tests/` directory:

```python
import os
import pytest
import requests
from python_magnetapi import utils

api_server = os.getenv("MAGNETDB_API_SERVER", "api.magnetdb-dev.local")
headers = {"Authorization": os.getenv("MAGNETDB_API_KEY")}


class TestMyFeature:
    def test_something(self):
        with requests.Session() as s:
            ids = utils.get_list(
                s, api_server, headers=headers,
                mtype="material"
            )
            assert len(ids) > 0
```

Pytest configuration is defined in `pyproject.toml` under
`[tool.pytest.ini_options]`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

## Coverage

Generate an HTML coverage report:

```bash
pytest --cov=python_magnetapi --cov-report=html
```

Open `htmlcov/index.html` in your browser to inspect the results.

Coverage configuration is in `pyproject.toml` under `[tool.coverage.run]`
and `[tool.coverage.report]`.
