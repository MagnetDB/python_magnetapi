# CLI Reference

`python_magnetapi` provides a command-line interface for interacting with
MagnetDB. The CLI supports listing, viewing, creating, deleting objects, as well
as setting up and running simulations.

## General Options

```text
python_magnetapi [--server SERVER] [--port PORT] [--debug] [--https]
                 {list,view,create,delete,setup,run,compute,process} ...
```

| Option | Description |
|--------|-------------|
| `--server` | MagnetDB API server hostname (default: `MAGNETDB_API_SERVER` env var or `api.magnetdb-dev.local`) |
| `--port` | API server port (default: `8000`, ignored with `--https`) |
| `--debug` | Enable debug output |
| `--https` | Use HTTPS instead of HTTP |

## Subcommands

### list

List objects of a given type.

```bash
python_magnetapi --https list --mtype material
```

Supported types: `material`, `part`, `magnet`, `site`, `record`,
`server`, `simulation`.

### view

View details of a specific object.

```bash
python_magnetapi --https view --mtype material --name testmat2
```

Options:

- `--mtype`: Object type
- `--name`: Object name

### create

Create a new object from inline JSON data or from a JSON file.

```bash
# From inline data
python_magnetapi --https create --mtype material --data '{"name": "tutu"}'

# From a file
python_magnetapi --https create --mtype material --file data.json
```

Options:

- `--mtype`: Object type
- `--data`: JSON data as a string (mutually exclusive with `--file`)
- `--file`: Path to a JSON file (mutually exclusive with `--data`)

### delete

Delete an object by name.

```bash
python_magnetapi --https delete --mtype material --name testmat2
```

### setup

Set up a simulation for a magnet or site.

```bash
python_magnetapi --https setup --mtype site --name M10_M19020601 \
  --method cfpdes --static --geometry Axi --model thelec \
  --cooling mean --current 31000 12000 100 \
  --wd path_to_store_setup
```

Options:

- `--mtype`: `magnet` or `site`
- `--name`: Object name
- `--geometry`: Geometry type (`Axi` or `3D`)
- `--method`: Numerical method (e.g. `cfpdes`)
- `--model`: Model name (e.g. `thelec`, `thmagel_hcurl`)
- `--cooling`: Cooling mode (`mean`, `meanH`, `grad`, `gradH`, `gradHZ`)
- `--current`: Requested current values
- `--static`: Enable static mode
- `--nonlinear`: Enable non-linear mode
- `--wd`: Working directory for output

### run

Run a previously set-up simulation.

```bash
python_magnetapi --https run --simu_id 42 --wd path_to_store_results
```

Options:

- `--simu_id`: Simulation ID (from the setup step)
- `--wd`: Working directory for results
- `--compute_server`: Compute node name (default: `calcul22`)
- `--np`: Number of MPI processes (default: `4`)

### compute

Compute derived quantities for an object.

```bash
# Flow parameters for a magnet
python_magnetapi --https compute --mtype magnet --name M19061901 --flow_params

# Hoop stress history for a part
python_magnetapi --https compute --mtype part --name H15101601 --hoop_stress

# Self and mutual inductances
python_magnetapi --https compute --mtype magnet --name M19061901 --inductances
```

Options:

- `--mtype`: `part`, `magnet`, `site`, or `record`
- `--name`: Object name
- `--flow_params`: Compute flow parameters (magnet only)
- `--hoop_stress`: Compute hoop stress history (part only)
- `--inductances`: Compute self and mutual inductances
- `--samples`: Number of samples to consider (default: `20`)
