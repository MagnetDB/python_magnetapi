#!/usr/bin/env python3
"""
demo_magnet_parts.py — Parts of a magnet
=========================================
For a given magnet name, retrieve all associated parts and display their
name, type, status, and material in a table.

Requires GET /api/magnets/{id}/parts to be available in magnetdb.

Usage
-----
    export MAGNETDB_API_SERVER=api.magnetdb-dev.local   # host only, no scheme
    export MAGNETDB_API_KEY=<your-key>
    python demo_magnet_parts.py --magnet M18110501

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
import enum

import requests
import urllib3
from rich.console import Console
from rich.table import Table

from python_magnetapi import utils
from python_magnetapi.cli.parser import add_server_arguments


class PartType(str, enum.Enum):
    """Part types as defined in MagnetDB."""

    HELIX = "helix"
    BITTER = "bitter"
    SUPRA = "supra"
    RING = "ring"
    SCREEN = "screen"
    LEAD = "lead"


def get_magnet_id(
    session, web: str, headers: dict, magnet_name: str, debug: bool
) -> int:
    """Resolve a magnet name to its numeric id."""
    ids = utils.get_list(session, web, headers=headers, mtype="magnet")
    if magnet_name not in ids:
        available = sorted(ids.keys())
        print(
            f"ERROR: magnet '{magnet_name}' not found.\n"
            f"Available magnets ({len(available)}): {available}"
        )
        sys.exit(1)
    return ids[magnet_name]


def main():
    parser = argparse.ArgumentParser(description="Show parts of a magnet")
    parser.add_argument("--magnet", required=True, help="Magnet name to inspect")
    parser.add_argument(
        "--type",
        type=PartType,
        choices=list(PartType),
        default=None,
        help="Filter parts by type (default: all types)",
    )
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
        r = session.get(f"{web}/api/magnets", headers=headers)
        if r.status_code != 200:
            console.print(
                f"[red]ERROR:[/red] cannot reach {web} (status {r.status_code})"
            )
            sys.exit(1)

        # resolve magnet name → id
        magnet_id = get_magnet_id(session, web, headers, args.magnet, args.debug)
        magnet = utils.get_object(
            session, web, headers=headers, mtype="magnet", id=magnet_id
        )

        console.print(f"\n[bold]Magnet:[/bold] {magnet.get('name')}  (id={magnet_id})")
        console.print()

        # fetch parts via GET /api/magnets/{id}/parts
        parts = utils.get_parts_for_magnet(session, web, headers, magnet_id)

        if args.type is not None:
            parts = [p for p in parts if p.get("type") == args.type.value]

        if not parts:
            console.print("[yellow]No parts found for this magnet.[/yellow]")
            return

        """
        # an alternative way of doing things?
        history = utils.get_history(
            session, web, headers, magnet_id, mtype="magnet", otype="part"
        )
        for row in history:
            print(f"raw magnet join-row: {row}")
        print(f"history: {[row.get('part').get('id') for row in history]}")
        """

        title = f"Parts of magnet '{args.magnet}'"
        if args.type is not None:
            title += f" (type={args.type.value})"
        table = Table(title=title)
        table.add_column("Part name", style="cyan", no_wrap=True)
        table.add_column("Type", style="white")
        table.add_column("Status", style="white")
        table.add_column("Material", style="green")

        for part in parts:
            # material_id is a direct FK column returned by model_serializer
            material_id = utils.get_fk_id(part, "material")
            if material_id is not None:
                mat = utils.get_object(
                    session,
                    web,
                    headers=headers,
                    mtype="material",
                    id=material_id,
                )
                material_name = (
                    mat.get("name", str(material_id)) if mat else str(material_id)
                )
            else:
                material_name = "—"

            table.add_row(
                part.get("name", "?"),
                part.get("type", "?"),
                part.get("status", "?"),
                material_name,
            )

        console.print(table)
        console.print()


if __name__ == "__main__":
    main()
