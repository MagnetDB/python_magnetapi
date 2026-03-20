"""Create command handler."""

import argparse
import json

from ..base import BaseCommand
from ..context import CLIContext


class CreateCommand(BaseCommand):
    """Create new object from JSON data or file."""

    name = "create"
    help = "Create new object"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure create command arguments."""
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
        command_group = parser.add_mutually_exclusive_group()
        command_group.add_argument(
            "--data",
            help="load data from dict",
            type=json.loads,
            nargs="?",
        )
        command_group.add_argument(
            "--file",
            help="load data from file",
            type=str,
            nargs="?",
        )

    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute create command.

        Args:
            args: Parsed arguments
            context: CLI context

        Returns:
            Exit code (0 for success)
        """
        from ...material import create as mat_create
        from ...site import create as site_create
        from ...magnet import create as magnet_create
        from ...part import create as part_create
        from ...record import create as record_create

        creators = {
            "material": mat_create,
            "site": site_create,
            "magnet": magnet_create,
            "part": part_create,
            "record": record_create,
        }

        data = {}
        if args.data:
            print(f"create: data={json.dumps(args.data, indent=4, default=str)}")
            data = args.data
        if args.file:
            print(f"create: file={args.file}")
            with open(args.file, "r") as f:
                data = json.loads(f.read())
                print(f"data: {data}")

        creator = creators[args.mtype]
        obj_id = creator(
            context.session,
            context.web,
            headers=context.headers,
            data=data,
            verbose=True,
            debug=context.debug,
        )

        if obj_id is None:
            print(f"create: type={args.mtype}, name={data.get('name')} not implemented")

        return 0
