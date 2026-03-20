"""Compute command handler."""

import argparse
from typing import Any, Dict

from ..base import BaseCommand
from ..context import CLIContext


class ComputeCommand(BaseCommand):
    """Compute derived quantities."""

    name = "compute"
    help = "Compute inductances, flow parameters, or hoop stress"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure compute command arguments.

        Args:
            parser: Subparser for this command
        """
        parser.add_argument(
            "--mtype",
            help="select object type",
            type=str,
            choices=["part", "magnet", "site", "record"],
            default="magnet",
        )
        parser.add_argument(
            "--name",
            help="specify an object name",
            type=str,
            default="None",
        )
        parser.add_argument(
            "--inductances",
            help="activate self and mutual inductances",
            action="store_true",
        )
        parser.add_argument(
            "--flow_params",
            help="activate flow params",
            action="store_true",
        )
        parser.add_argument(
            "--hoop_stress",
            help="activate hoop stress history",
            action="store_true",
        )
        parser.add_argument(
            "--samples",
            help="specify number of samples to consider",
            type=int,
            default=20,
        )

    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute compute command.

        Args:
            args: Parsed arguments
            context: CLI context

        Returns:
            Exit code (0 for success)
        """
        if args.inductances:
            self._compute_inductances(args, context)

        if args.flow_params:
            self._compute_flow_params(args, context)

        if args.hoop_stress:
            self._compute_hoop_stress(args, context)

        return 0

    def _compute_inductances(
        self, args: argparse.Namespace, context: CLIContext
    ) -> None:
        """Compute self and mutual inductances.

        Args:
            args: Parsed arguments (requires mtype, name)
            context: CLI context
        """
        self.validate_resource_type(args.mtype, ["magnet", "site", "record"])

        obj: Dict[str, Any] = self.get_object_by_name(context, args.mtype, args.name)

        from ... import inductances

        print("Compute Self/Mutual inductances")
        inductances.compute(
            context.session,
            context.web,
            context.headers,
            oid=obj["id"],
            mtype=args.mtype,
        )

    def _compute_flow_params(
        self, args: argparse.Namespace, context: CLIContext
    ) -> None:
        """Compute flow parameters.

        Args:
            args: Parsed arguments (requires mtype=magnet, name, samples)
            context: CLI context
        """
        self.validate_resource_type(args.mtype, ["magnet"])

        obj: Dict[str, Any] = self.get_object_by_name(context, args.mtype, args.name)

        from ... import flow_params

        flow_params.compute(
            context.session,
            context.web,
            headers=context.headers,
            oid=obj["id"],
            samples=args.samples,
        )

    def _compute_hoop_stress(
        self, args: argparse.Namespace, context: CLIContext
    ) -> None:
        """Compute hoop stress.

        Args:
            args: Parsed arguments (requires mtype=part, name)
            context: CLI context
        """
        self.validate_resource_type(args.mtype, ["part"])

        obj: Dict[str, Any] = self.get_object_by_name(context, args.mtype, args.name)

        from ... import hoop_stress

        hoop_stress.compute(
            context.session,
            context.web,
            headers=context.headers,
            mtype=args.mtype,
            oid=obj["id"],
        )
