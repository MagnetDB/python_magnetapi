#!/usr/bin/env python3
"""
Demonstrator 2 – Part history with site details & records
==========================================================
Extends Demonstrator 1: for every site in which a part was used (via its
magnets) also display:
  • site metadata  (status, commission / decommission dates, description)
  • names of every measurement record attached to that site

All magnets and sites are sorted chronologically.

Usage
-----
    export MAGNETDB_API_SERVER=api.magnetdb-dev.local
    export MAGNETDB_API_KEY=<your-key>
    python demo_part_site_records.py --part H22121601

Optional flags
--------------
    --server   override MAGNETDB_API_SERVER
    --https    use HTTPS (default: HTTP on port 8000)
    --json     dump full site payloads as JSON at the end
    --debug    print raw API responses
"""

import os
import sys
import json
import argparse
from datetime import datetime

import requests

from python_magnetapi import utils


# ---------------------------------------------------------------------------
# Date helpers  (shared with demo_part_history.py)
# ---------------------------------------------------------------------------

_DATE_FIELDS = ("commissioned_at", "decommissioned_at", "created_at", "updated_at")


def _parse_date(obj: dict, field: str | None = None) -> datetime:
    """Return a datetime parsed from *field* (or the first available date field)."""
    fields = [field] if field else _DATE_FIELDS
    for f in fields:
        raw = obj.get(f)
        if raw:
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(raw, fmt)
                except ValueError:
                    continue
    return datetime.min


def _date_str(obj: dict, field: str | None = None) -> str:
    dt = _parse_date(obj, field)
    return dt.strftime("%Y-%m-%d %H:%M") if dt != datetime.min else "—"


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def get_part_id(session, web, headers, part_name, debug) -> int:
    ids = utils.get_list(session, web, headers=headers, mtype="part")
    if part_name not in ids:
        print(
            f"ERROR: part '{part_name}' not found.\n"
            f"Available: {sorted(ids.keys())}"
        )
        sys.exit(1)
    return ids[part_name]


def get_magnets_for_part(session, web, headers, part_id, debug) -> list[dict]:
    r = session.get(f"{web}/api/parts/{part_id}/magnets", headers=headers)
    if r.status_code != 200:
        if debug:
            print(f"[debug] GET /api/parts/{part_id}/magnets → {r.status_code}: {r.text}")
        return []

    join_rows = r.json()
    magnets, seen = [], set()
    for row in join_rows:
        mid = row.get("magnet_id")
        if mid and mid not in seen:
            seen.add(mid)
            obj = utils.get_object(
                session, web, headers=headers, mtype="magnet", id=mid
            )
            if obj:
                magnets.append(obj)

    return sorted(magnets, key=_parse_date)


def get_sites_for_magnet(session, web, headers, magnet_id, debug) -> list[dict]:
    join_rows = utils.get_history(
        session, web, headers, magnet_id, mtype="magnet", otype="site"
    )
    if not join_rows:
        return []

    sites, seen = [], set()
    for row in join_rows:
        sid = row.get("id") or row.get("site_id")
        if sid and sid not in seen:
            seen.add(sid)
            obj = utils.get_object(
                session, web, headers=headers, mtype="site", id=sid
            )
            if obj:
                sites.append(obj)

    return sorted(sites, key=_parse_date)


def get_records_for_site(session, web, headers, site_id, debug) -> list[dict]:
    """
    Return all record objects attached to *site_id*.

    The API exposes  GET /api/sites/{id}/records.
    Each record has at minimum: id, name, created_at, attachment_id.
    """
    records = utils.get_history(
        session, web, headers, site_id, mtype="site", otype="record"
    )
    if not records:
        return []
    return sorted(records, key=lambda r: _parse_date(r, "created_at"))


# ---------------------------------------------------------------------------
# Pretty printers
# ---------------------------------------------------------------------------

_SEP  = "─" * 70
_SEP2 = "·" * 60

def print_site_card(site: dict, records: list[dict], magnet_names: list[str]) -> None:
    """Print a formatted card for one site with its records."""
    print(f"\n  {'▶':>2}  {site.get('name', '?')}   (id={site.get('id', '?')})")
    print(f"       status        : {site.get('status', '—')}")
    print(f"       description   : {site.get('description') or '—'}")
    print(f"       commissioned  : {_date_str(site, 'commissioned_at')}")
    print(f"       decommissioned: {_date_str(site, 'decommissioned_at')}")
    print(f"       created       : {_date_str(site, 'created_at')}")

    if magnet_names:
        print(f"       magnets       : {', '.join(magnet_names)}")

    if records:
        print(f"       records ({len(records):>3}) :")
        for rec in records:
            rdate = _date_str(rec, "created_at")
            print(f"                        [{rdate}]  {rec.get('name', '?')}")
    else:
        print(f"       records       : (none)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    api_server = os.getenv("MAGNETDB_API_SERVER") or "api.magnetdb-dev.local"

    parser = argparse.ArgumentParser(
        description="Show part history with full site data and associated records"
    )
    parser.add_argument("--part",   required=True, help="Part name to inspect")
    parser.add_argument("--server", default=api_server)
    parser.add_argument("--port",   type=int, default=8000)
    parser.add_argument("--https",     action="store_true")
    parser.add_argument("--no-verify", action="store_true",
                        help="Skip TLS certificate verification (self-signed certs)")
    parser.add_argument("--json",   action="store_true", help="Dump raw site JSON at end")
    parser.add_argument("--debug",  action="store_true")
    args = parser.parse_args()

    web = (
        f"https://{args.server}"
        if args.https
        else f"http://{args.server}:{args.port}"
    )
    headers = {"Authorization": os.getenv("MAGNETDB_API_KEY", "")}

    if args.no_verify:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    with requests.Session() as session:
        session.verify = not args.no_verify
        # health-check
        r = session.get(f"{web}/api/magnets", headers=headers)
        if r.status_code != 200:
            print(f"ERROR: cannot reach {web} (status {r.status_code})")
            sys.exit(1)

        # ── Banner ────────────────────────────────────────────────────────
        print(f"\n{'='*70}")
        print(f"  Part history + site details + records")
        print(f"  Part  : {args.part}")
        print(f"  Server: {web}")
        print(f"{'='*70}")

        # ── 1. Part ───────────────────────────────────────────────────────
        part_id = get_part_id(session, web, headers, args.part, args.debug)
        part = utils.get_object(
            session, web, headers=headers, mtype="part", id=part_id
        )
        print(f"\nPart details")
        print(f"  name     : {part.get('name')}")
        print(f"  type     : {part.get('type')}")
        print(f"  status   : {part.get('status')}")
        print(f"  ref      : {part.get('design_office_reference', '—')}")
        print(f"  created  : {_date_str(part, 'created_at')}")

        # ── 2. Magnets ────────────────────────────────────────────────────
        magnets = get_magnets_for_part(session, web, headers, part_id, args.debug)
        print(f"\n{_SEP}")
        print(f"Magnets containing this part  ({len(magnets)}, sorted by date)")
        print(_SEP)
        for m in magnets:
            print(f"  [{_date_str(m, 'created_at')}]  {m.get('name')}  (id={m.get('id')})")
        if not magnets:
            print("  (none found)")

        # ── 3. Sites (deduplicated) ───────────────────────────────────────
        # Build: site_id → (site_obj, [magnet_names_that_link_to_it])
        site_map: dict[int, tuple[dict, list[str]]] = {}
        for m in magnets:
            for site in get_sites_for_magnet(session, web, headers, m["id"], args.debug):
                sid = site["id"]
                if sid not in site_map:
                    site_map[sid] = (site, [])
                site_map[sid][1].append(m["name"])

        sorted_sites = sorted(
            site_map.values(),
            key=lambda pair: _parse_date(pair[0]),
        )

        print(f"\n{_SEP}")
        print(
            f"Sites that used this part (via its magnets)  "
            f"({len(sorted_sites)}, sorted by date)"
        )
        print(_SEP)

        raw_sites = []
        for site_obj, mnames in sorted_sites:
            records = get_records_for_site(
                session, web, headers, site_obj["id"], args.debug
            )
            print_site_card(site_obj, records, mnames)
            raw_sites.append(site_obj)

        if not sorted_sites:
            print("  (none found)")

        # ── 4. Optional JSON dump ─────────────────────────────────────────
        if args.json and raw_sites:
            print(f"\n{_SEP}")
            print("Raw site JSON")
            print(_SEP)
            print(json.dumps(raw_sites, indent=2, default=str))

        print()


if __name__ == "__main__":
    main()
