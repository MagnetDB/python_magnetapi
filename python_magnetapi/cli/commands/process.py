"""Process command handler."""

import argparse

from ..base import BaseCommand
from ..context import CLIContext


class ProcessCommand(BaseCommand):
    """Process/post-process simulation results."""

    name = "process"
    help = "Process simulation results (not yet implemented)"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure process command arguments.

        Args:
            parser: Subparser for this command
        """
        pass

    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute process command.

        Args:
            args: Parsed arguments
            context: CLI context

        Returns:
            Exit code
        """
        print("process: not implemented")
        return 0
