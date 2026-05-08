# MagnetDB Part History — Demonstrators

Two stand-alone scripts that query the MagnetDB REST API to trace the
operational history of a magnet **part** (helix, bitter, or supra insert).

Both scripts rely only on `python_magnetapi.utils` and the standard
`requests` library; no simulation setup or `magnettools` bindings are
required.

---

## Prerequisites

| Variable | Description |
|---|---|
| `MAGNETDB_API_KEY` | Personal API token (copy from your profile page on MagnetDB) |
| `MAGNETDB_API_SERVER` | Hostname of the API server — host only, no scheme (e.g. `api.magnetdb.local`) |

```bash
export MAGNETDB_API_KEY=xxxxxxxxxxxx
export MAGNETDB_API_SERVER=api.magnetdb.local
```

Both scripts accept `--server` on the command line to override the environment
variable without changing your shell.

---

## Demo 1 — `demo_part_history.py`

### What it does

Given a part name, retrieves and prints:

1. **Part metadata** — name, type, status
2. **Magnets** that have ever contained this part, sorted chronologically
3. **Sites** (experimental stations) in which those magnets were used,
   deduplicated and sorted chronologically

The date used for sorting is `commissioned_at` when available, falling back
to `created_at`.

### API calls made

```
GET /api/parts            → resolve name → id
GET /api/parts/{id}       → part metadata
GET /api/parts/{id}/magnets  → join rows → magnet ids
GET /api/magnets/{id}     → magnet metadata  (one call per magnet)
GET /api/magnets/{id}/sites  → join rows → site ids
GET /api/sites/{id}       → site metadata    (one call per site)
```

### Usage

```bash
python demo_part_history.py --part H22121601
```

### All flags

| Flag | Default | Description |
|---|---|---|
| `--part` | *(required)* | Part name to inspect |
| `--server` | `$MAGNETDB_API_SERVER` | API hostname (no scheme) |
| `--port` | `8000` | Port (HTTP only) |
| `--https` | off | Use HTTPS instead of HTTP |
| `--debug` | off | Print raw JSON API responses |

### Sample output

```
============================================================
  Part history for: H22121601
  Server          : http://api.magnetdb.local:8000
============================================================

Part details
  name   : H22121601
  type   : helix
  status : in_stock

Magnets containing this part  (3 found, sorted by date)
  [2021-06-18]  HL-31  (id=12)
  [2022-01-05]  HL-34  (id=47)
  [2023-03-12]  HL-36  (id=61)

Sites that used this part (via its magnets)  (2 found, sorted by date)
  [2022-03-01]  M9_M18110501   (id=5)
  [2023-01-20]  M10_M19020601  (id=9)
```

---

## Demo 2 — `demo_part_site_records.py`

### What it does

Extends Demo 1 with richer information for every site:

1. **Part metadata** — as in Demo 1
2. **Magnets** — as in Demo 1
3. **Sites** with full detail cards, each showing:
   - Status, description
   - Commission and decommission dates
   - Which magnets (from the part's history) link to this site
   - **All measurement records** attached to the site, sorted by creation date

Optionally dumps the raw site JSON payloads with `--json`.

### API calls made

Same as Demo 1, plus:

```
GET /api/sites/{id}/records  → record list with names and dates
```

### Usage

```bash
python demo_part_site_records.py --part H22121601
```

With JSON dump:

```bash
python demo_part_site_records.py --part H22121601 --json
```

### All flags

| Flag | Default | Description |
|---|---|---|
| `--part` | *(required)* | Part name to inspect |
| `--server` | `$MAGNETDB_API_SERVER` | API hostname (no scheme) |
| `--port` | `8000` | Port (HTTP only) |
| `--https` | off | Use HTTPS instead of HTTP |
| `--json` | off | Dump raw site JSON payloads at end of output |
| `--debug` | off | Print raw JSON API responses |

### Sample output

```
======================================================================
  Part history + site details + records
  Part  : H22121601
  Server: http://api.magnetdb.local:8000
======================================================================

Part details
  name     : H22121601
  type     : helix
  status   : in_stock
  ref      : —
  created  : 2021-06-18 10:32

──────────────────────────────────────────────────────────────────────
Magnets containing this part  (3, sorted by date)
──────────────────────────────────────────────────────────────────────
  [2021-06-18 10:32]  HL-31  (id=12)
  [2022-01-05 09:15]  HL-34  (id=47)
  [2023-03-12 14:00]  HL-36  (id=61)

──────────────────────────────────────────────────────────────────────
Sites that used this part (via its magnets)  (2, sorted by date)
──────────────────────────────────────────────────────────────────────

  ▶  M9_M18110501   (id=5)
     status        : decommissioned
     description   : 9 T insert magnet cell
     commissioned  : 2022-03-01 08:00
     decommissioned: 2023-11-15 17:30
     magnets       : HL-31, HL-34
     records (  42) :
                    [2022-03-22 09:27]  M9_2022.03.22---09:27:56.txt
                    [2022-04-01 14:05]  M9_2022.04.01---14:05:12.txt
                    ...

  ▶  M10_M19020601  (id=9)
     status        : in_use
     description   : 10 T insert magnet cell
     commissioned  : 2023-01-20 11:00
     decommissioned: —
     magnets       : HL-36
     records ( 118) :
                    [2023-01-25 08:41]  M10_2023.01.25---08:41:03.txt
                    ...
```

---

## Demo 3 — `calcul_DT_helices_from_api.py`

### What it does

Computes the **conductor temperature rise** for every helix of a resistive
magnet using the same physical model as `calcul_DT_helices_HL31.py`.
Geometry and material data are obtained through one of three selectable
backends (chosen automatically based on which flags are supplied):

| Backend | Trigger flag | What is read |
|---|---|---|
| **magnettools** (preferred) | `--dfile PATH` | Pre-generated `.d` input file via pybind11 bindings |
| **JSON file** | `--magnet-json PATH` | Fully-expanded JSON with embedded geometry + material |
| **API + YAML** (fallback) | *(neither flag)* | Per-helix geometry YAMLs downloaded from MagnetDB; material from API |

### Physical model

For each helix (inner radius $R_\text{int}$, outer radius $R_\text{ext}$,
pitch $h_\text{spire}$, current $I$):

$$e = \frac{D_\text{ext} - D_\text{int}}{2}, \quad
j = \frac{I}{e \cdot h_\text{spire}}$$

$$P_\text{vol} = \rho \, j^2, \quad
\text{flux} = P_\text{vol} \cdot \frac{D_\text{ext} - D_\text{int}}{4}$$

$$\Delta T_\text{paroi} = \frac{\text{flux}}{h_\text{conv}}, \quad
\Delta T_\text{plane} = \frac{P_\text{vol}\,e^2}{8\,\lambda}$$

$$T_\text{max} = T_\text{eau} + \Delta T_\text{paroi} + \Delta T_\text{plane}$$

A Matthiessen consistency check derives `T_moy_ro` and `Rapport IACS` from ρ.

### API calls made (API + YAML backend only)

```
GET /api/magnets           → resolve name → id
GET /api/magnets/{id}      → part list
GET /api/parts/{id}        → part metadata + geometry attachments
GET /api/attachments/{id}  → download geometry YAML
```

### Usage

```bash
# API + YAML fallback (requires MAGNETDB_API_KEY):
python calcul_DT_helices_from_api.py M9 --current 31000

# With a pre-generated magnettools .d file (preferred):
python calcul_DT_helices_from_api.py M9 --current 31000 --dfile M9.d

# With a JSON file containing magnet definition:
python calcul_DT_helices_from_api.py M9 --current 31000 --magnet-json M9.json

# Override cooling defaults:
python calcul_DT_helices_from_api.py M9 --current 31000 --h_conv 85000 --Teau 30

# Full server specification with HTTPS:
python calcul_DT_helices_from_api.py M9 --current 31000 \
    --server magnetdb.lncmi.local --https
```

### All flags

| Flag | Default | Description |
|---|---|---|
| `magnet` | *(required)* | Magnet name (e.g. `M9`, `HL31`) |
| `--current / -I` | *(required)* | Operating current [A] |
| `--dfile PATH` | — | Path to magnettools `.d` input file |
| `--magnet-json PATH` | — | Path to JSON file with magnet definition |
| `--server` | `$MAGNETDB_API_SERVER` | API hostname (no scheme) |
| `--port` | — | Port number |
| `--https` | off | Use HTTPS instead of HTTP |
| `--h_conv` | `85000` | Heat-transfer coefficient [W/m²/°C] |
| `--Teau` | `30` | Cooling water temperature [°C] |
| `--rho` | — | Override resistivity ρ [Ω·m] for all helices |
| `--lam` | — | Override thermal conductivity λ [W/m/°C] for all helices |
| `--verbose` | off | Print full transposed DataFrame (all columns) |
| `--debug` | off | Print raw API responses and intermediate values |

### Sample output

```
====================================================================================================
Calcul températures hélices — M9  (I = 31000 A)
====================================================================================================
    DT_paroi [°C]  DT_plane [°C]  DT_cyl [°C]  Tmax [°C]  Tmoy [°C]  T_moy_ro [°C]  Rapport IACS
H1          12.34          18.72        19.05      61.06      42.83          48.21        0.9231
H2          11.87          17.45        17.74      59.32      41.45          46.98        0.9312
H3          10.92          15.63        15.87      56.55      39.67          45.11        0.9418
...

Tmax range: 54.3 … 65.1 °C
Tmoy range: 38.7 … 44.2 °C
```

---

## Relationship between the demos

```
demo_part_history.py          demo_part_site_records.py
─────────────────────         ──────────────────────────────────────
part metadata          ──▶    part metadata
magnets (sorted)       ──▶    magnets (sorted)
sites (sorted)         ──▶    sites (sorted) + full card per site
                                └── status, dates, description
                                └── linked magnet names
                                └── all record names (sorted)
                       (opt)   raw JSON dump  (--json)
```

```
calcul_DT_helices_from_api.py
──────────────────────────────────────────────────────────────────────
magnet name + current  ──▶  helix geometry (dfile / JSON / API+YAML)
                       ──▶  material (ρ, λ)  from same source
                       ──▶  ΔT_paroi, ΔT_plane, Tmax, Tmoy per helix
```

Demo 1 is useful for a quick chronological overview.
Demo 2 is the starting point for further analysis such as hoop-stress
history computation (`hoop_stress.py`), which consumes the record list
exposed by each site card.
Demo 3 is a standalone thermal check tool: given a magnet name and
operating current it reports per-helix temperature rises and Matthiessen
consistency, using whichever data source is available.
