# Documentation for python_magnetapi

This directory contains the Sphinx documentation for the `python_magnetapi` package.

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
pip install -e ".[doc]"
```

This installs:
- sphinx
- sphinx-rtd-theme
- myst-parser

Optionally, for better type hint rendering:
```bash
pip install sphinx-autodoc-typehints
```

### Build HTML Documentation

On Linux/macOS:

```bash
cd docs
make html
```

On Windows:

```bash
cd docs
make.bat html
```

The generated HTML documentation will be in `_build/html/`. Open `_build/html/index.html` in your browser.

### Other Build Targets

- `make clean` - Remove build artifacts
- `make latexpdf` - Build PDF documentation (requires LaTeX)
- `make linkcheck` - Check all external links

## Documentation Structure

```
docs/
├── conf.py              # Sphinx configuration
├── index.md             # Main documentation page
├── installation.md      # Installation instructions
├── quickstart.md        # Quick start guide
├── configuration.md     # Server & environment configuration
├── cli.md               # CLI reference
├── usage.md             # Advanced usage guide
├── testing.md           # Testing guide
├── contributing.md      # Contributing guide
├── api/                 # API reference (autodoc)
│   ├── index.md
│   ├── utils.md
│   ├── cli_module.md
│   ├── material.md
│   ├── part.md
│   ├── magnet.md
│   ├── site.md
│   ├── geometry.md
│   ├── record.md
│   ├── analysis.md
│   ├── hoop_stress.md
│   ├── hoop_stress_parallel.md
│   ├── inductances.md
│   └── flow_params.md
├── Makefile             # Unix build script
├── make.bat             # Windows build script
└── _templates/          # Custom Sphinx templates
```

## Auto-documentation

The API documentation is automatically generated from docstrings using Sphinx's
autodoc extension. Docstrings should follow Google or NumPy style conventions.
