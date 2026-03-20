"""Base command handler class."""

from abc import ABC, abstractmethod
import argparse
from typing import Optional, List, Dict

from .context import CLIContext
from .. import utils
from ..exceptions import ResourceNotFoundError, ValidationError


class BaseCommand(ABC):
    """Base class for all CLI command handlers.

    Subclasses should implement:
        - name: Command name
        - help: Command help text
        - configure_parser(): Add command-specific arguments
        - execute(): Execute command logic
    """

    name: str = ""
    help: str = ""

    @abstractmethod
    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure argument parser for this command.

        Args:
            parser: Subparser for this command
        """
        pass

    @abstractmethod
    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute the command.

        Args:
            args: Parsed command-line arguments
            context: CLI context with session and configuration

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        pass

    def get_object_list(self, context: CLIContext, mtype: str) -> Dict[str, int]:
        """Get list of objects by type.

        Args:
            context: CLI context
            mtype: Resource type (material, part, magnet, etc.)

        Returns:
            Dictionary mapping names to IDs
        """
        return utils.get_list(
            context.session,
            context.web,
            headers=context.headers,
            mtype=mtype,
            debug=context.debug,
        )

    def get_object_by_name(
        self, context: CLIContext, mtype: str, name: str
    ) -> dict:
        """Get object by name.

        Args:
            context: CLI context
            mtype: Resource type
            name: Object name

        Returns:
            Object data dictionary

        Raises:
            ResourceNotFoundError: If object doesn't exist
        """
        ids = self.get_object_list(context, mtype)

        if name not in ids:
            raise ResourceNotFoundError(
                f"{mtype} '{name}' not found",
                object_name=name,
                object_type=mtype,
            )

        return utils.get_object(
            context.session,
            context.web,
            context.headers,
            ids[name],
            mtype,
            debug=context.debug,
        )

    def validate_resource_type(
        self,
        mtype: str,
        allowed_types: List[str],
        command_name: Optional[str] = None,
    ) -> None:
        """Validate that resource type is allowed for this command.

        Args:
            mtype: Resource type to validate
            allowed_types: List of allowed types
            command_name: Command name for error message

        Raises:
            ValidationError: If type is not allowed
        """
        if mtype not in allowed_types:
            cmd = command_name or self.name
            raise ValidationError(
                f"Command '{cmd}' does not support resource type '{mtype}'. "
                f"Expected one of: {allowed_types}",
                provided_type=mtype,
                expected_types=allowed_types,
            )
