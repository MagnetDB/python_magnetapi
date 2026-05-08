# Contributing

## Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/Trophime/python_magnetapi.git
   cd python_magnetapi
   ```

2. Create a virtual environment and install in editable mode:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -e ".[dev,doc]"
   ```

3. Run the tests to make sure everything works:

   ```bash
   export MAGNETDB_API_KEY=your_api_key_here
   pytest --verbose
   ```

## Code Style

The project uses [Black](https://black.readthedocs.io/) for code formatting.
Format your code before committing:

```bash
black python_magnetapi/ tests/
```

## Building Documentation

Build the HTML documentation locally:

```bash
cd docs
make html
```

The output will be in `docs/_build/html/`. Open `index.html` in your
browser to preview.

To check for broken links:

```bash
make linkcheck
```

## Adding New Modules

When adding a new module to `python_magnetapi`:

1. Create the module file in `python_magnetapi/`
2. Add docstrings following the Google or NumPy style
3. Create a corresponding `.md` file in `docs/api/`
4. Add the new `.md` file to `docs/api/index.md`
5. Write tests in `tests/`
6. Build the docs and verify the autodoc output

## Debian Packaging

When updating the package version:

1. Update `version` in `pyproject.toml`
2. Update the Debian changelog:

   ```bash
   dch -v 0.2.0-1 "New upstream release"
   ```

3. Rebuild the package:

   ```bash
   ./archive.sh -v 0.2.0 -d trixie
   ```
