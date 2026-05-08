# Python MagnetAPI

Python CLI and library for interacting with MagnetDB — a database for magnetic materials, parts, magnets, and sites.

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

`python_magnetapi` provides utilities to interact with MagnetDB, including:

- Listing, viewing, creating, and deleting objects (materials, parts, magnets, sites, records, servers, simulations)
- Setting up and running simulations
- Computing derived quantities (inductances, flow parameters, hoop stress)
- Post-processing simulation results

## Installation

### Requirements

- Python >= 3.11
- A running MagnetDB instance

### Option 1: Install within a Python virtual environment (recommended for development)

```bash
git clone https://github.com/MagnetDB/python_magnetapi.git
cd python_magnetapi

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

Alternatively, you can use the provided helper script:

```bash
./start-venv.sh
source venv/bin/activate
```

This script creates a virtual environment with `--system-site-packages` enabled (useful when system-level dependencies like `python3-magnetsetup` are installed via apt) and installs the package in editable mode.

To use `uv` instead of pip:

```bash
uv venv venv
source venv/bin/activate
uv pip install -e ".[dev]"
```

### Option 2: Debian packaging

#### Installing from the LNCMI Debian repository

If the package is available in the LNCMI Debian repository:

```bash
sudo apt update
sudo apt install python3-magnetapi
```

#### Building the Debian package locally

Install the required build tools:

```bash
sudo apt install debhelper dh-python python3-all python3-setuptools \
                 devscripts build-essential
```

Install build dependencies listed in `debian/control`:

```bash
sudo apt install python3-magnetrun python3-magnetsetup python3-rich
```

Build the package:

```bash
# Using the archive script (recommended)
./archive.sh -v 0.1.0 -d trixie

# Or manually
dpkg-buildpackage -us -uc -b
```

Install the resulting `.deb` file:

```bash
sudo dpkg -i ../python3-magnetapi_0.1.0-1_all.deb
sudo apt install -f  # Fix any missing dependencies
```

### Option 3: Using a Docker container

A DevContainer configuration is provided in `.devcontainer/` for use with VS Code or any OCI-compatible runtime.

#### Building the Docker image

```bash
docker build -f .devcontainer/Dockerfile -t magnetapi:latest .
```

#### Running the container

```bash
docker run -it --net host \
  -e MAGNETDB_API_KEY=${MAGNETDB_API_KEY} \
  magnetapi:latest
```

For development with VS Code, simply open the project folder and select **"Reopen in Container"** when prompted. The DevContainer will automatically build the image, install all dependencies (including `python3-magnetrun`, `python3-magnetsetup`, and `python3-rich` from the LNCMI Debian repository), and configure Python tooling.

#### Using a Singularity/Apptainer container

You can convert the Docker image to a Singularity/Apptainer container, which is particularly useful for HPC environments:

```bash
# Build from the local Docker image
singularity build magnetapi.sif docker-daemon://magnetapi:latest

# Or with Apptainer
apptainer build magnetapi.sif docker-daemon://magnetapi:latest
```

Run the container:

```bash
singularity exec magnetapi.sif python -m python_magnetapi.cli --help
# or
apptainer exec magnetapi.sif python -m python_magnetapi.cli --help
```

## Pre-requisites

### MagnetDB client

Ensure the MagnetDB server is accessible. Add the following entries to `/etc/hosts` with the appropriate IP address:

```
aa.bb.xx.yy magnetdb.local
aa.bb.xx.yy api.magnetdb.local
aa.bb.xx.yy lemon.magnetdb.local
aa.bb.xx.yy manager.lemon.magnetdb.local
aa.bb.xx.yy auth.lemon.magnetdb.local
aa.bb.xx.yy pgadmin.magnetdb.local
aa.bb.xx.yy minio.magnetdb.local
aa.bb.xx.yy traefik.magnetdb.local
```

### Add the CA certificate

Retrieve and install the server certificate:

```bash
echo | openssl s_client -servername magnetdb.local -connect magnetdb.local:443 | cat > magnetdb.crt
sudo cp magnetdb.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

### API key

Obtain your API key from your profile page on `magnetdb.local` and export it:

```bash
export MAGNETDB_API_KEY=your_api_key_here
```

## Usage

### CLI

The CLI is accessible either as a console script or via `python -m`:

```bash
# Using the installed entry point
python_magnetapi --help

# Or using the module directly
python -m python_magnetapi.cli --help
```

### Examples

#### Listing objects

List commands now display results as formatted tables:

```bash
# List all materials (displays as a formatted table)
python -m python_magnetapi.cli --https list --mtype material

# List all parts
python -m python_magnetapi.cli --https list --mtype part

# List all magnets
python -m python_magnetapi.cli --https list --mtype magnet

# List all sites
python -m python_magnetapi.cli --https list --mtype site
```

**Example output:**
```
PART: found 53 items
           Name  ID
       HL-34_H1   1
       HL-34_H2   2
      Ring-H1H2   3
           tore   4
          tore1   5
...
```

#### Filtering results

Filter objects by their attributes using `--filter KEY=VALUE`. Multiple filters can be combined:

```bash
# Filter parts by a single attribute
python -m python_magnetapi.cli --https list --mtype part --filter status=active

# Filter with multiple attributes (all must match)
python -m python_magnetapi.cli --https list --mtype part --filter status=active --filter type=helix

# Filter magnets by site
python -m python_magnetapi.cli --https list --mtype magnet --filter site=grenoble

# Filter materials by property
python -m python_magnetapi.cli --https list --mtype material --filter material_type=copper
```

#### Viewing and creating objects

```bash
# View a specific material
python -m python_magnetapi.cli --https view --mtype material --name testmat2

# Create a material from inline JSON
python -m python_magnetapi.cli --https create --mtype material --data '{"name": "tutu"}'

# Create a material from a JSON file
python -m python_magnetapi.cli --https create --mtype material --file data.json

# Delete a material
python -m python_magnetapi.cli --https delete --mtype material --name testmat2
```

#### Computing derived quantities

```bash
# Compute flow parameters for a magnet
python -m python_magnetapi.cli --https compute --mtype magnet --name M19061901 --flow_params

# Compute hoop stress for a part
python -m python_magnetapi.cli --https compute --mtype part --name H15101601 --hoop_stress
```

#### Setting up and running simulations

```bash
# Setup a simulation
python -m python_magnetapi.cli --https setup --mtype site --name M10_M19020601 \
   --method cfpdes --static --geometry Axi --model thelec --cooling mean \
   --current 31000 12000 100 \
   --wd path_to_store_setup

# Run a simulation
python -m python_magnetapi.cli --https run --simu_id id --wd path_to_store_results
```

### As a library

```python
import requests
from python_magnetapi import utils

headers = {"Authorization": "your_api_key"}
web = "https://api.magnetdb.local"

with requests.Session() as s:
    # List all magnets
    ids = utils.get_list(s, web, headers=headers, mtype="magnet")
    
    # List with filters (single attribute)
    active_parts = utils.get_list(
        s, web, headers=headers, mtype="part",
        filters={"status": "active"}
    )
    
    # List with multiple filters (all must match)
    filtered_magnets = utils.get_list(
        s, web, headers=headers, mtype="magnet",
        filters={"site": "grenoble", "status": "operational"}
    )
    
    # Get a specific object
    obj = utils.get_object(s, web, headers=headers, mtype="magnet", id=ids["M19061901"])
```

#### Analysis registry

The `analysis` subpackage exposes a lightweight registry for post-processing computations. Built-in analyses are loaded lazily — their heavy optional dependencies (`magnettools`, `python_magnetcooling`, …) are only imported when the analysis is actually run.

```python
from python_magnetapi.analysis import names, get, register

# Discover available analyses
print(names())
# ['inductances', 'flow_params', 'hoop_stress', 'hoop_stress_parallel']

# Run a built-in analysis (deps loaded here, not at import time)
entry = get("hoop_stress")
print(entry["mtypes"])   # ['part']
df = entry["compute"](session, web, headers=headers, mtype="part", oid=part_id)
```

Third-party packages can add their own analyses without modifying this package:

```python
# In your package's __init__.py or plugin module:
from python_magnetapi.analysis import register

register(
    "my_analysis",
    module="my_package.my_module",   # must expose a compute() function
    mtypes=["magnet", "site"],
    help="My custom post-processing",
)
```

Alternatively, declare an entry point in `pyproject.toml` for automatic discovery:

```toml
[project.entry-points."python_magnetapi.analysis"]
my_analysis = "my_package.my_module"
```

## Testing

The test suite is split into two tiers:

| Tier | Location | Requires live server? |
|------|----------|-----------------------|
| CLI unit/integration | `tests/cli/` | No — uses mocks |
| API integration | `tests/test_list.py` | Yes |

### CLI tests (no server required)

```bash
# Run only the CLI tests
pytest tests/cli/ --verbose

# Run with coverage
pytest tests/cli/ --cov=python_magnetapi.cli --cov-report=term
```

### Full integration tests

API integration tests require a running MagnetDB instance and a valid API key:

```bash
export MAGNETDB_API_KEY=your_api_key_here

# Run all tests
pytest

# Run with verbose output
pytest --verbose

# Run with coverage report
pytest --cov=python_magnetapi --cov-report=html --cov-report=term
```

### Testing inside a Docker container

When testing against a local MagnetDB instance running in Docker:

```bash
export MAGNETDB_API_KEY=test
export MAGNETDB_API_SERVER=http://localhost:8000
pytest --verbose
```

### Writing new tests

Tests live in the `tests/` directory. Create files following the `test_*.py` naming convention.
CLI command handlers can be tested without a live server by mocking `utils.get_list` and
`utils.get_object`:

```python
import pytest
from unittest.mock import patch, Mock
from python_magnetapi.cli.commands.list import ListCommand
from python_magnetapi.cli.context import CLIContext

def test_list_command():
    context = Mock(spec=CLIContext)
    context.web = "http://test:8000"
    context.headers = {"Authorization": "key"}
    context.debug = False

    with patch("python_magnetapi.utils.get_list", return_value={"M10": 1}):
        cmd = ListCommand()
        args = Mock(mtype="magnet", filters=None)
        assert cmd.execute(args, context) == 0
```

Pytest configuration is defined in `pyproject.toml` under `[tool.pytest.ini_options]`.

## Project structure

```
python_magnetapi/
├── __init__.py          # Package metadata and version
├── cli/                 # CLI package
│   ├── __init__.py      # Entry point — main() function
│   ├── base.py          # BaseCommand ABC and OBJECT_TYPES constant
│   ├── context.py       # CLIContext dataclass (session, headers, URL)
│   ├── parser.py        # Argument parser factory
│   └── commands/        # One module per subcommand
│       ├── list.py
│       ├── view.py
│       ├── create.py
│       ├── delete.py
│       ├── setup.py
│       ├── run.py
│       ├── compute.py
│       └── process.py
├── utils.py             # Core API interaction utilities
├── material.py          # Material-specific operations
├── part.py              # Part-specific operations
├── magnet.py            # Magnet-specific operations
├── site.py              # Site-specific operations
├── geometry.py          # Geometry attachment utilities
├── record.py            # Record management
├── attachment.py        # Generic attachment helpers
└── analysis/            # Post-processing analyses (registry-based)
    ├── __init__.py      # Registry: register() / get() / names()
    ├── inductances.py   # Self and mutual inductances
    ├── flow_params.py   # Flow parameters from measurement records
    ├── hoop_stress.py   # Hoop stress history (sequential)
    └── hoop_stress_parallel.py  # Hoop stress history (parallel)
tests/                   # Test suite
├── cli/                 # Unit/integration tests for the CLI (no server needed)
│   ├── test_list_command.py
│   └── test_cli_integration.py
└── test_list.py         # Integration tests (require a running MagnetDB instance)

debian/                  # Debian packaging files
.devcontainer/           # Docker/DevContainer configuration
pyproject.toml           # Project metadata and build configuration
start-venv.sh            # Helper script for virtual environment setup
```

## Authors

- **Christophe Trophime** — <christophe.trophime@lncmi.cnrs.fr>
- **Remi Caumette** — <remicaumette@icloud.com>

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Links

- **Repository**: <https://github.com/MagnetDB/python_magnetapi>
- **Bug Tracker**: <https://github.com/MagnetDB/python_magnetapi/issues>
