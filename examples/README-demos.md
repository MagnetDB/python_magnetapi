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

## Relationship between the two demos

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

Demo 1 is useful for a quick chronological overview.
Demo 2 is the starting point for further analysis such as hoop-stress
history computation (`hoop_stress.py`), which consumes the record list
exposed by each site card.
