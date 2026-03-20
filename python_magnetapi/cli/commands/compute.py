"""Compute command handler."""

import argparse

from ..base import BaseCommand
from ..context import CLIContext
from ... import utils
from ...exceptions import ValidationError


class ComputeCommand(BaseCommand):
    """Compute derived quantities."""

    name = "compute"
    help = "Compute inductances, flow parameters, or hoop stress"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure compute command arguments."""
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
        """Compute self and mutual inductances."""
        if args.mtype in ["part"]:
            raise RuntimeError(
                f"unexpected type {args.mtype} in compute subcommand inductances"
            )

        ids = self.get_object_list(context, args.mtype)
        if args.name not in ids:
            raise RuntimeError(
                f"unexpected name {args.name}: no such object found in"
                f" {args.mtype} list: {list(ids.keys())}"
            )

        utils.get_object(
            context.session,
            context.web,
            context.headers,
            ids[args.name],
            args.mtype,
            debug=context.debug,
        )

        from ... import inductances

        print("Compute Self/Mutual inductances")
        inductances.compute(
            context.session,
            context.web,
            context.headers,
            oid=ids[args.name],
            mtype=args.mtype,
            debug=context.debug,
        )

    def _compute_flow_params(
        self, args: argparse.Namespace, context: CLIContext
    ) -> None:
        """Compute flow parameters."""
        if args.mtype != "magnet":
            raise RuntimeError(
                f"unexpected type {args.mtype} in compute subcommand flow_params"
                " - should be magnet"
            )

        ids = self.get_object_list(context, args.mtype)
        if args.name not in ids:
            raise RuntimeError(
                f"cannot found {args.name} in {args.mtype.upper()} objects"
            )

        utils.get_object(
            context.session,
            context.web,
            context.headers,
            ids[args.name],
            args.mtype,
            debug=context.debug,
        )

        from ... import flow_params

        flow_params.compute(
            context.session,
            context.web,
            headers=context.headers,
            oid=ids[args.name],
            samples=args.samples,
            debug=context.debug,
        )

    def _compute_hoop_stress(
        self, args: argparse.Namespace, context: CLIContext
    ) -> None:
        """Compute hoop stress."""
        if args.mtype not in ["part"]:
            raise RuntimeError(
                f"unexpected type {args.mtype} in compute subcommand hoop_stress"
            )

        ids = self.get_object_list(context, args.mtype)
        if args.name not in ids:
            raise RuntimeError(
                f"cannot found {args.name} in {args.mtype.upper()} objects"
            )

        utils.get_object(
            context.session,
            context.web,
            context.headers,
            ids[args.name],
            args.mtype,
            debug=context.debug,
        )

        from ... import hoop_stress

        hoop_stress.compute(
            context.session,
            context.web,
            headers=context.headers,
            mtype=args.mtype,
            oid=ids[args.name],
            debug=context.debug,
        )
