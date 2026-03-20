"""List command handler."""

import argparse
from typing import Dict, Optional

from ..base import BaseCommand, OBJECT_TYPES
from ..context import CLIContext
from ... import utils


class ListCommand(BaseCommand):
    """List objects of a given type."""

    name = "list"
    help = "List objects in MagnetDB"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure list command arguments.

        Args:
            parser: Subparser for this command
        """
        parser.add_argument(
            "--mtype",
            help="select object type",
            type=str,
            choices=OBJECT_TYPES,
            default="magnet",
        )
        parser.add_argument(
            "--filter",
            help="filter results by attribute (format: key=value). Can be used multiple times.",
            action="append",
            dest="filters",
            metavar="KEY=VALUE",
        )

    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute list command.

        Args:
            args: Parsed arguments
            context: CLI context

        Returns:
            Exit code (0 for success)
        """
        filter_dict: Dict[str, str] = {}
        if args.filters:
            for filter_str in args.filters:
                if "=" in filter_str:
                    key, value = filter_str.split("=", 1)
                    filter_dict[key.strip()] = value.strip()
                else:
                    print(
                        f"Warning: Invalid filter format '{filter_str}'. Expected KEY=VALUE"
                    )

        ids = utils.get_list(
            context.session,
            context.web,
            headers=context.headers,
            mtype=args.mtype,
            filters=filter_dict if filter_dict else None,
            debug=context.debug,
        )
        print(f"{args.mtype.upper()}: found {len(ids)} items")

        import pandas as pd

        data = [{"Name": name, "ID": id_value} for name, id_value in ids.items()]
        df = pd.DataFrame(data)
        print(df.to_string(index=False))

        return 0
