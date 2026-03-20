#! /usr/bin/python3

"""CLI for interacting with MagnetDB."""

import os
import sys
from typing import List, Optional

from .parser import create_parser
from .context import CLIContext
from .commands import COMMANDS
from ..exceptions import MagnetAPIException, AuthenticationError


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entry point.

    Args:
        argv: Command-line arguments (for testing); uses sys.argv if None

    Returns:
        Exit code (0 for success)
    """
    parser = create_parser(COMMANDS)
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.debug:
        print(f"args: {args}")

    api_key = os.getenv("MAGNETDB_API_KEY")
    if not api_key:
        raise AuthenticationError(
            "API key not found. Please set the MAGNETDB_API_KEY environment variable. "
            "You can obtain your API key from your profile page on MagnetDB."
        )

    context = CLIContext(
        server=args.server,
        port=args.port,
        api_key=api_key,
        debug=args.debug,
        https=args.https,
    )

    command = COMMANDS[args.command]()

    with context:
        return command.execute(args, context)


if __name__ == "__main__":
    sys.exit(main())
