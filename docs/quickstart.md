# Quick Start

This guide walks you through the basic usage of `python_magnetapi`.

## Prerequisites

Make sure you have:

1. Installed the package (see {doc}`installation`)
2. Configured access to MagnetDB (see {doc}`configuration`)
3. Exported your API key:

   ```bash
   export MAGNETDB_API_KEY=your_api_key_here
   ```

## Using the CLI

The CLI is accessible either as a console script or via `python -m`:

```bash
# Using the installed entry point
python_magnetapi --help

# Or using the module directly
python -m python_magnetapi.cli --help
```

List all materials:

```bash
python -m python_magnetapi.cli --https list --mtype material
```

View a specific material:

```bash
python -m python_magnetapi.cli --https view --mtype material --name testmat2
```

Create a material from inline JSON:

```bash
python -m python_magnetapi.cli --https create --mtype material \
  --data '{"name": "tutu"}'
```

## Using the Library

You can also use `python_magnetapi` as a Python library for programmatic
access:

```python
import os
import requests
from python_magnetapi import utils

api_server = os.getenv("MAGNETDB_API_SERVER", "api.magnetdb-dev.local")
headers = {"Authorization": os.getenv("MAGNETDB_API_KEY")}
web = f"https://{api_server}"

with requests.Session() as s:
    # Verify connectivity
    r = s.get(f"{web}/api/magnets", headers=headers, verify=True)
    r.raise_for_status()

    # List all magnets
    ids = utils.get_list(s, web, headers=headers, mtype="magnet")
    for name, obj_id in ids.items():
        print(f"Magnet: {name} (id={obj_id})")

    # Get a specific object
    if "M19061901" in ids:
        obj = utils.get_object(
            s, web, headers=headers,
            mtype="magnet", id=ids["M19061901"]
        )
        print(obj)
```

## Next Steps

- See {doc}`cli` for the full CLI reference
- See {doc}`usage` for advanced usage patterns
- See the {doc}`api/index` for the complete Python API reference
