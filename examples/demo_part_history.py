#!/usr/bin/env python3
"""
Demonstrator 1 – Part history
==============================
For a given part name, retrieve:
  • all magnets in which this part was ever installed
  • all sites (experimental stations) in which those magnets were used
Both lists are sorted chronologically by their commission date
(``commissioned_at``) when available, falling back to ``created_at``.

Usage
-----
    export MAGNETDB_API_SERVER=api.magnetdb-dev.local   # host only, no scheme
    export MAGNETDB_API_KEY=<your-key>
    python demo_part_history.py --part H22121601

Optional flags
--------------
    --server  override MAGNETDB_API_SERVER
    --https   use HTTPS instead of HTTP (default: HTTP on port 8000)
    --debug   print raw API responses
"""

import os
import sys
import json
import argparse
from datetime import datetime

import requests

from python_magnetapi import utils


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DATE_FIELDS = ("commissioned_at", "created_at", "updated_at")


def _parse_date(obj: dict) -> datetime:
    """Return the earliest parseable date from an API object dict."""
    for field in _DATE_FIELDS:
        raw = obj.get(field)
        if raw:
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(raw, fmt)
                except ValueError:
                    continue
    return datetime.min


def _fmt(obj: dict) -> str:
    """Human-readable one-liner for an object."""
    dt = _parse_date(obj)
    date_str = dt.strftime("%Y-%m-%d") if dt != datetime.min else "date unknown"
    return f"  [{date_str}]  {obj.get('name', '?')}  (id={obj.get('id', '?')})"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def get_part_id(session, web: str, headers: dict, part_name: str, debug: bool) -> int:
    """Resolve a part name to its numeric id."""
    ids = utils.get_list(session, web, headers=headers, mtype="part")
    if part_name not in ids:
        available = sorted(ids.keys())
        print(
            f"ERROR: part '{part_name}' not found.\n"
            f"Available parts ({len(available)}): {available}"
        )
        sys.exit(1)
    return ids[part_name]


def get_magnets_for_part(
    session, web: str, headers: dict, part_id: int, debug: bool
) -> list[dict]:
    """
    Return every magnet object that contains *part_id*.

    The MagnetDB API exposes  GET /api/parts/{id}/magnets  which returns the
    list of MagnetPart join-rows; each row carries ``magnet_id``.  We then
    fetch the full magnet object to get its metadata (name, dates, …).
    """
    r = session.get(f"{web}/api/parts/{part_id}/magnets", headers=headers)
    if r.status_code != 200:
        print(f"WARNING: GET /api/parts/{part_id}/magnets → {r.status_code}")
        if debug:
            print(r.text)
        return []

    join_rows = r.json()
    if debug:
        print(f"[debug] magnet join-rows: {json.dumps(join_rows, indent=2, default=str)}")

    magnets = []
    seen = set()
    for row in join_rows:
        mid = row.get("magnet_id")
        if mid is None or mid in seen:
            continue
        seen.add(mid)
        magnet = utils.get_object(
            session, web, headers=headers, mtype="magnet", id=mid
        )
        if magnet:
            magnets.append(magnet)

    magnets.sort(key=_parse_date)
    return magnets


def get_sites_for_magnet(
    session, web: str, headers: dict, magnet_id: int, debug: bool
) -> list[dict]:
    """
    Return every site that hosted *magnet_id*, with full site objects.
    """
    join_rows = utils.get_history(
        session, web, headers, magnet_id, mtype="magnet", otype="site"
    )
    if not join_rows:
        return []

    sites = []
    seen = set()
    for row in join_rows:
        # get_history returns raw rows; the site id may live under 'id' or 'site_id'
        sid = row.get("id") or row.get("site_id")
        if sid is None or sid in seen:
            continue
        seen.add(sid)
        site = utils.get_object(
            session, web, headers=headers, mtype="site", id=sid
        )
        if site:
            sites.append(site)

    sites.sort(key=_parse_date)
    return sites


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    api_server = os.getenv("MAGNETDB_API_SERVER") or "api.magnetdb-dev.local"

    parser = argparse.ArgumentParser(description="Show part history (magnets & sites)")
    parser.add_argument("--part",   required=True, help="Part name to inspect")
    parser.add_argument("--server", default=api_server, help="API server hostname")
    parser.add_argument("--port",   type=int, default=8000, help="Port (HTTP only)")
    parser.add_argument("--https",     action="store_true", help="Use HTTPS")
    parser.add_argument("--no-verify", action="store_true",
                        help="Skip TLS certificate verification (self-signed certs)")
    parser.add_argument("--debug",  action="store_true", help="Verbose API output")
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
        # --- health-check ---------------------------------------------------
        r = session.get(f"{web}/api/magnets", headers=headers)
        if r.status_code != 200:
            print(f"ERROR: cannot reach {web} (status {r.status_code})")
            sys.exit(1)

        print(f"\n{'='*60}")
        print(f"  Part history for: {args.part}")
        print(f"  Server          : {web}")
        print(f"{'='*60}\n")

        # 1. Resolve part
        part_id = get_part_id(session, web, headers, args.part, args.debug)
        part = utils.get_object(
            session, web, headers=headers, mtype="part", id=part_id
        )
        print(f"Part details")
        print(f"  name   : {part.get('name')}")
        print(f"  type   : {part.get('type')}")
        print(f"  status : {part.get('status')}")
        print()

        # 2. Magnets that include this part
        magnets = get_magnets_for_part(session, web, headers, part_id, args.debug)

        print(f"Magnets containing this part  ({len(magnets)} found, sorted by date)")
        print("-" * 60)
        if magnets:
            for m in magnets:
                print(_fmt(m))
        else:
            print("  (none found)")
        print()

        # 3. Sites for each magnet (deduplicated, globally sorted)
        all_sites: dict[int, dict] = {}
        for m in magnets:
            for site in get_sites_for_magnet(
                session, web, headers, m["id"], args.debug
            ):
                all_sites[site["id"]] = site

        sorted_sites = sorted(all_sites.values(), key=_parse_date)

        print(f"Sites that used this part (via its magnets)  ({len(sorted_sites)} found, sorted by date)")
        print("-" * 60)
        if sorted_sites:
            for s in sorted_sites:
                print(_fmt(s))
        else:
            print("  (none found)")
        print()


if __name__ == "__main__":
    main()
