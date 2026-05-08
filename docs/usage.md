# Usage Guide

This guide covers advanced usage patterns for `python_magnetapi`.

## Object Types

MagnetDB organizes data into the following object types:

- **material**: Physical materials with properties (conductivity, density, etc.)
- **part**: Individual components (helices, bitter disks, supra coils) made of a material
- **magnet**: An assembly of parts
- **site**: A physical installation containing one or more magnets
- **record**: Experimental measurement data attached to a site
- **server**: Compute servers for running simulations
- **simulation**: Simulation configurations and results

## CRUD Operations

All object types support the basic CRUD (Create, Read, Update, Delete) workflow.

### Creating objects with dependencies

When creating a **part**, you must specify its material. The material can be
referenced by name (if it already exists in the database) or provided as a
nested dictionary to be created on the fly:

```python
from python_magnetapi.part import create as part_create

# Reference existing material by name
data = {
    "name": "H22121601",
    "type": "helix",
    "material": "CuAg",
}
part_create(session, web, headers=headers, data=data)
```

Similarly, **magnets** reference parts and **sites** reference magnets.

## Simulation Workflow

A typical simulation workflow consists of three steps:

1. **Setup**: Configure the simulation parameters
2. **Run**: Execute the simulation on a compute server
3. **Post-process**: Analyze and retrieve results

```bash
# Step 1: Setup
python_magnetapi --https setup --mtype site --name M10_M19020601 \
  --method cfpdes --geometry Axi --model thelec --cooling mean \
  --current 31000 12000 100 --wd ./setup_output

# Step 2: Run (use the simulation ID from setup)
python_magnetapi --https run --simu_id 42 --wd ./run_output
```

## Computing Derived Quantities

### Flow parameters

Compute flow parameters for a magnet by fitting experimental record data:

```bash
python_magnetapi --https compute --mtype magnet \
  --name M19061901 --flow_params --samples 20
```

### Hoop stress

Compute the hoop stress history for a part across all sites where it has
been installed:

```bash
python_magnetapi --https compute --mtype part \
  --name H15101601 --hoop_stress
```

This retrieves the operational history (records) for each site, extracts
current data, and calculates the mechanical stress on the part.

### Inductances

Compute self and mutual inductances for a magnet:

```bash
python_magnetapi --https compute --mtype magnet \
  --name M19061901 --inductances
```

## Working with the Python API

### Session management

The library uses `requests.Session` objects for HTTP connection pooling:

```python
import os
import requests
from python_magnetapi import utils

headers = {"Authorization": os.getenv("MAGNETDB_API_KEY")}
web = "https://api.magnetdb.local"

with requests.Session() as s:
    # All API calls share the same session
    ids = utils.get_list(s, web, headers=headers, mtype="magnet")
    for name, oid in ids.items():
        obj = utils.get_object(s, web, headers=headers, mtype="magnet", id=oid)
        print(f"{name}: {obj}")
```

### Pagination

The `get_list` function handles pagination automatically, iterating through
all pages of results and returning a complete dictionary of `{name: id}`
pairs.

### File attachments

Objects can have associated files (geometries, CAD files, records). Use the
utility functions to manage attachments:

```python
# Download an attachment
filename = utils.download(session, web, headers, attach_id, wd="./downloads")

# Add a geometry file to a part
utils.add_data_files_to_object(
    session, web, headers,
    id=part_id,
    mtype="part",
    dtype="geometrie",
    data={"type": "default"},
    files={"geometry": "H15101601.yaml"},
)
```
