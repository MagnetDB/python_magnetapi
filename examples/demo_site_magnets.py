#!/usr/bin/env python3
"""
demo_site_magnets.py — Magnets of a site
=========================================
For a given site name, retrieve all associated magnets and display their
name, status, and number of parts in a table.

Requires GET /api/sites/{id}/magnets to be available in magnetdb.

Usage
-----
    export MAGNETDB_API_SERVER=api.magnetdb-dev.local   # host only, no scheme
    export MAGNETDB_API_KEY=<your-key>
    python demo_site_magnets.py --site M10_M19020601

Optional flags
--------------
    --server     override MAGNETDB_API_SERVER
    --https      use HTTPS instead of HTTP (default: HTTP on port 8000)
    --no-verify  skip TLS certificate verification (self-signed certs)
    --debug      print raw API responses
"""

import os
import sys
import argparse

import requests
import urllib3
from rich.console import Console
from rich.table import Table

from python_magnetapi import utils
from python_magnetapi.cli.parser import add_server_arguments


def get_site_id(
    session, web: str, headers: dict, site_name: str, debug: bool
) -> int:
    """Resolve a site name to its numeric id."""
    ids = utils.get_list(session, web, headers=headers, mtype="site")
    if site_name not in ids:
        available = sorted(ids.keys())
        print(
            f"ERROR: site '{site_name}' not found.\n"
            f"Available sites ({len(available)}): {available}"
        )
        sys.exit(1)
    return ids[site_name]


def main():
    parser = argparse.ArgumentParser(description="Show magnets of a site")
    parser.add_argument("--site", required=True, help="Site name to inspect")
    add_server_arguments(parser)
    args = parser.parse_args()

    web = (
        f"https://{args.server}" if args.https else f"http://{args.server}:{args.port}"
    )
    headers = {"Authorization": os.getenv("MAGNETDB_API_KEY", "")}

    if args.no_verify:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    console = Console()

    with requests.Session() as session:
        session.verify = not args.no_verify
        # health-check
        r = session.get(f"{web}/api/sites", headers=headers)
        if r.status_code != 200:
            console.print(
                f"[red]ERROR:[/red] cannot reach {web} (status {r.status_code})"
            )
            sys.exit(1)

        # resolve site name → id
        site_id = get_site_id(session, web, headers, args.site, args.debug)
        site = utils.get_object(
            session, web, headers=headers, mtype="site", id=site_id
        )

        console.print(f"\n[bold]Site:[/bold] {site.get('name')}  (id={site_id})")
        console.print()

        # fetch magnets via GET /api/sites/{id}/magnets
        magnets = utils.get_magnets_for_site(session, web, headers, site_id)

        if args.debug:
            history = utils.get_history(
                session, web, headers, site_id, mtype="site", otype="magnet"
            )
            for row in history:
                print(f"raw site join-row: {row}")

        if not magnets:
            console.print("[yellow]No magnets found for this site.[/yellow]")
            return

        table = Table(title=f"Magnets of site '{args.site}'")
        table.add_column("Magnet name", style="cyan", no_wrap=True)
        table.add_column("Status", style="white")
        table.add_column("# Parts", style="green", justify="right")

        for magnet in magnets:
            parts = utils.get_parts_for_magnet(session, web, headers, magnet["id"])
            table.add_row(
                magnet.get("name", "?"),
                magnet.get("status", "?"),
                str(len(parts)),
            )

        console.print(table)
        console.print()


if __name__ == "__main__":
    main()
