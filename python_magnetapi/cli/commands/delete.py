"""Delete command handler."""

import argparse

from ..base import BaseCommand, OBJECT_TYPES
from ..context import CLIContext
from ... import utils
from ...exceptions import ResourceNotFoundError


class DeleteCommand(BaseCommand):
    """Delete object by name."""

    name = "delete"
    help = "Delete object"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure delete command arguments.

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
            "--name",
            help="specify an object name",
            type=str,
            default="None",
        )

    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute delete command.

        Args:
            args: Parsed arguments
            context: CLI context

        Returns:
            Exit code (0 for success)
        """
        ids = self.get_object_list(context, args.mtype)

        if args.name not in ids:
            raise ResourceNotFoundError(
                f"Object '{args.name}' not found in {args.mtype} collection",
                object_name=args.name,
                object_type=args.mtype,
            )

        print(f"{args.name}: id={ids[args.name]}")
        utils.del_object(
            context.session,
            context.web,
            headers=context.headers,
            mtype=args.mtype,
            id=ids[args.name],
            verbose=True,
            debug=context.debug,
        )

        return 0
