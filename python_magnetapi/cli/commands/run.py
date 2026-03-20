"""Run command handler."""

import argparse
import sys
from time import sleep
from typing import Any, Dict, Optional

from ..base import BaseCommand
from ..context import CLIContext
from ... import utils


class RunCommand(BaseCommand):
    """Run a simulation."""

    name = "run"
    help = "Run simulation"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure run command arguments.

        Args:
            parser: Subparser for this command
        """
        parser.add_argument(
            "--mtype",
            help="select object type",
            type=str,
            choices=["magnet", "site"],
            default="magnet",
        )
        parser.add_argument(
            "--simu_id",
            help="select simulation id",
            type=int,
            default=-1,
        )
        parser.add_argument(
            "--wd",
            help="select directory to store setup/simulation results",
            type=str,
            default=".",
        )
        parser.add_argument(
            "--compute_server",
            help="choose compute node",
            type=str,
            default="calcul22",
        )
        parser.add_argument(
            "--np",
            help="choose number of procs",
            type=int,
            default=4,
        )

    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute run command.

        Args:
            args: Parsed arguments
            context: CLI context

        Returns:
            Exit code (0 for success)
        """
        simu: Optional[Dict[str, Any]] = utils.get_object(
            context.session,
            context.web,
            context.headers,
            args.simu_id,
            mtype="simulation",
            debug=context.debug,
        )
        if simu is None:
            raise RuntimeError(
                f"run: cannot find {args.simu_id} simulation"
                " - please check simulations list"
            )

        server_ids: Dict[str, int] = utils.get_list(
            context.session,
            context.web,
            headers=context.headers,
            mtype="server",
            debug=context.debug,
        )
        if args.compute_server not in server_ids:
            raise RuntimeError(
                f"{args.compute_server}: cannot found {args.compute_server} in server objects"
            )
        server_id: int = server_ids[args.compute_server]

        print("Starting simulation...")
        context.session.post(
            f"{context.web}/api/simulations/{args.simu_id}/run",
            data={"server_id": server_id},
            headers=context.headers,
        )

        while True:
            simulation = utils.get_object(
                context.session,
                context.web,
                context.headers,
                args.simu_id,
                mtype="simulation",
                debug=context.debug,
            )
            if simulation["status"] in ["failed", "done"]:
                break
            sleep(10)

        print(f'Simulation done: status={simulation["status"]}')
        if simulation["status"] == "failed":
            sys.exit(1)

        print(f"simulation={simulation}")
        simu_arch_id = simulation["output_attachment"]["id"]
        simu_filename = utils.download(
            context.session,
            context.web,
            headers=context.headers,
            attach=simu_arch_id,
            wd=args.wd,
            debug=context.debug,
        )
        print(f"{simu_filename} downloaded")
        print(f'simulation {simulation["id"]} done')

        return 0
