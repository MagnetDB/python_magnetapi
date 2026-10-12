"""Command registry and imports."""

from typing import Dict, Type

from ..base import BaseCommand
from .compute import ComputeCommand
from .create import CreateCommand
from .delete import DeleteCommand
from .list import ListCommand
from .process import ProcessCommand
from .run import RunCommand
from .setup import SetupCommand
from .view import ViewCommand

COMMANDS: dict[str, type[BaseCommand]] = {
    "list": ListCommand,
    "view": ViewCommand,
    "create": CreateCommand,
    "delete": DeleteCommand,
    "setup": SetupCommand,
    "run": RunCommand,
    "compute": ComputeCommand,
    "process": ProcessCommand,
}

__all__ = ["COMMANDS"]
