"""Command registry and imports."""

from typing import Dict, Type

from ..base import BaseCommand
from .list import ListCommand
from .view import ViewCommand
from .create import CreateCommand
from .delete import DeleteCommand
from .setup import SetupCommand
from .run import RunCommand
from .compute import ComputeCommand
from .process import ProcessCommand


COMMANDS: Dict[str, Type[BaseCommand]] = {
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
