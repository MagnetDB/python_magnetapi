"""View command handler."""

import argparse
import json

from ..base import BaseCommand
from ..context import CLIContext


class ViewCommand(BaseCommand):
    """View details of a specific object."""

    name = "view"
    help = "View object details"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure view command arguments."""
        parser.add_argument(
            "--mtype",
            help="select object type",
            type=str,
            choices=[
                "material",
                "part",
                "magnet",
                "site",
                "record",
                "server",
                "simulation",
            ],
            default="magnet",
        )
        parser.add_argument(
            "--name",
            help="specify an object name",
            type=str,
            default="None",
        )

    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute view command.

        Args:
            args: Parsed arguments
            context: CLI context

        Returns:
            Exit code (0 for success)
        """
        ids = self.get_object_list(context, args.mtype)
        print(f"view: ids={ids}")

        obj = self.get_object_by_name(context, args.mtype, args.name)
        print(f"{args.name}:\n{json.dumps(obj, indent=4)}")

        return 0
