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
git clone https://github.com/Trophime/python_magnetapi.git
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

### MagnetDB server

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

```bash
# List all materials
python -m python_magnetapi.cli --https list --mtype material

# View a specific material
python -m python_magnetapi.cli --https view --mtype material --name testmat2

# Create a material from inline JSON
python -m python_magnetapi.cli --https create --mtype material --data '{"name": "tutu"}'

# Create a material from a JSON file
python -m python_magnetapi.cli --https create --mtype material --file data.json

# Delete a material
python -m python_magnetapi.cli --https delete --mtype material --name testmat2

# Compute flow parameters for a magnet
python -m python_magnetapi.cli --https compute --mtype magnet --name M19061901 --flow_params

# Compute hoop stress for a part
python -m python_magnetapi.cli --https compute --mtype part --name H15101601 --hoop_stress

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
    ids = utils.get_list(s, web, headers=headers, mtype="magnets")
    
    # Get a specific object
    obj = utils.get_object(s, web, headers=headers, mtype="magnets", id=ids["M19061901"])
```

## Testing

### Running the test suite

Tests require a running MagnetDB instance and a valid API key:

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

Tests live in the `tests/` directory. Create files following the `test_*.py` naming convention:

```python
import pytest
from python_magnetapi import utils

class TestUtils:
    def test_get_list(self):
        """Test listing objects from the API."""
        # ...
```

Pytest configuration is defined in `pyproject.toml` under `[tool.pytest.ini_options]`.

## Project structure

```
python_magnetapi/
├── __init__.py          # Package metadata and version
├── cli.py               # CLI entry point with subcommands
├── utils.py             # Core API interaction utilities
├── material.py          # Material-specific operations
├── part.py              # Part-specific operations
├── magnet.py            # Magnet-specific operations
├── site.py              # Site-specific operations
└── ...
tests/                   # Test suite
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

- **Repository**: <https://github.com/Trophime/python_magnetapi>
- **Bug Tracker**: <https://github.com/Trophime/python_magnetapi/issues>
