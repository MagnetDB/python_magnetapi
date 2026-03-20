"""Argument parser configuration."""

import argparse
import os
from typing import Dict, Type

from .base import BaseCommand


def add_server_arguments(parser: argparse.ArgumentParser) -> None:
    """Add standard server/connection arguments to any parser.

    Args:
        parser: ArgumentParser (or subparser) to augment
    """
    parser.add_argument(
        "--server",
        help="API server hostname",
        type=str,
        default=os.getenv("MAGNETDB_API_SERVER", "api.magnetdb-dev.local"),
    )
    parser.add_argument(
        "--port",
        help="API server port",
        type=int,
        default=8000,
    )
    parser.add_argument(
        "--https",
        help="Use HTTPS",
        action="store_true",
    )
    parser.add_argument(
        "--no-verify",
        help="Skip TLS certificate verification (self-signed certs)",
        action="store_true",
    )
    parser.add_argument(
        "--debug",
        help="Enable debug mode",
        action="store_true",
    )


def add_logging_arguments(parser: argparse.ArgumentParser) -> None:
    """Add logging-related arguments to any parser.

    Args:
        parser: ArgumentParser (or subparser) to augment
    """
    parser.add_argument(
        "--log-level",
        help="Logging level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="WARNING",
    )
    parser.add_argument(
        "--log-file",
        help="Optional file path to write logs to",
        type=str,
        default=None,
    )


def create_parser(commands: Dict[str, Type[BaseCommand]]) -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Args:
        commands: Dictionary of command name to command class

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="python_magnetapi",
        description="CLI for interacting with MagnetDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    add_server_arguments(parser)
    add_logging_arguments(parser)

    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="Available commands",
    )

    for cmd_name, cmd_class in commands.items():
        cmd_instance = cmd_class()
        cmd_parser = subparsers.add_parser(
            cmd_name,
            help=cmd_instance.help,
        )
        cmd_instance.configure_parser(cmd_parser)

    return parser
