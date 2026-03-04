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
├── index.rst            # Main documentation page
├── installation.rst     # Installation instructions
├── quickstart.rst       # Quick start guide
├── configuration.rst    # Server & environment configuration
├── cli.rst              # CLI reference
├── usage.rst            # Advanced usage guide
├── testing.rst          # Testing guide
├── contributing.rst     # Contributing guide
├── api/                 # API reference (autodoc)
│   ├── index.rst
│   ├── utils.rst
│   ├── cli_module.rst
│   ├── material.rst
│   ├── part.rst
│   ├── magnet.rst
│   ├── site.rst
│   ├── geometry.rst
│   ├── record.rst
│   ├── hoop_stress.rst
│   └── flow_params.rst
├── Makefile             # Unix build script
├── make.bat             # Windows build script
├── _static/             # Static files (CSS, images)
└── _templates/          # Custom Sphinx templates
```

## Auto-documentation

The API documentation is automatically generated from docstrings using Sphinx's
autodoc extension. Docstrings should follow Google or NumPy style conventions.
