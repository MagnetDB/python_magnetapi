"""Setup command handler."""

import argparse
import sys
from time import sleep

from ..base import BaseCommand
from ..context import CLIContext
from ... import utils
from ...exceptions import ValidationError


class SetupCommand(BaseCommand):
    """Setup simulation for magnet or site."""

    name = "setup"
    help = "Setup simulation"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure setup command arguments."""
        parser.add_argument(
            "--mtype",
            help="select object type",
            type=str,
            choices=["magnet", "site"],
            default="magnet",
        )
        parser.add_argument(
            "--name",
            help="specify an object name",
            type=str,
            default="None",
        )
        parser.add_argument(
            "--current",
            help="specify requested current (default: 31kA)",
            nargs="+",
            metavar="Current",
            type=float,
            default=[31.0e3],
        )
        parser.add_argument(
            "--geometry",
            help="select a method",
            type=str,
            choices=["Axi", "3D"],
            default="Axi",
        )
        parser.add_argument(
            "--static",
            help="activate static mode",
            action="store_true",
        )
        parser.add_argument(
            "--nonlinear",
            help="activate non_linear",
            action="store_true",
        )
        parser.add_argument(
            "--method",
            help="select a method",
            type=str,
            default="cfpdes",
        )
        parser.add_argument(
            "--model",
            help="select a model",
            type=str,
            default="thmagel_hcurl",
        )
        parser.add_argument(
            "--cooling",
            help="select a cooling mode",
            type=str,
            choices=["mean", "meanH", "grad", "gradH", "gradHZ"],
            default="meanH",
        )
        parser.add_argument(
            "--wd",
            help="select directory to store setup/simulation results",
            type=str,
            default=".",
        )

    def execute(self, args: argparse.Namespace, context: CLIContext) -> int:
        """Execute setup command.

        Args:
            args: Parsed arguments
            context: CLI context

        Returns:
            Exit code (0 for success)
        """
        self.validate_resource_type(args.mtype, ["magnet", "site"])

        # Check consistent method and model
        r = context.session.get(
            f"{context.web}/api/simulations/models", headers=context.headers
        )
        response = r.json()
        if r.status_code != 200:
            raise RuntimeError(
                f"setup: cannot get models dict {response['detail']}"
            )

        available_methods = [
            data["method"]
            for data in response
            if data["geometry"] == args.geometry
        ]
        available_methods = list(set(available_methods))
        if args.method not in available_methods:
            raise RuntimeError(
                f"{args.method}: unknown method for {args.geometry} geometry"
                f" - supported values are {available_methods}"
            )

        available_models = {}
        for method in available_methods:
            available_models[method] = [
                data["model"]
                for data in response
                if data["method"] == args.method and data["geometry"] == args.geometry
            ]
        if args.model not in available_models[args.method]:
            raise RuntimeError(
                f"{args.model}: unknown model for {args.method} and {args.geometry}"
                f" geometry - supported values are {available_models[args.method]}"
            )

        ids = self.get_object_list(context, args.mtype)
        if args.name not in ids:
            raise RuntimeError(
                f"run: cannot found {args.name} in {args.mtype.upper()} objects"
            )

        obj = utils.get_object(
            context.session,
            context.web,
            context.headers,
            ids[args.name],
            mtype=args.mtype,
            verbose=True,
            debug=context.debug,
        )

        currents = []
        if args.mtype == "site":
            if len(args.current) != len(obj["site_magnets"]):
                raise RuntimeError(
                    f"args.current contains {len(args.current)} values"
                    f" - should have {len(obj['site_magnets'])} values"
                )
            for i, magnet in enumerate(obj["site_magnets"]):
                print(f"current[{i}]: magnet={magnet}")
                currents.append(
                    {"magnet_id": magnet["magnet_id"], "value": args.current[i]}
                )
        else:
            if len(args.current) != 1:
                raise RuntimeError(
                    f"args.current contains {len(args.current)} values - should have 1 value"
                )
            currents.append({"magnet_id": ids[args.name], "value": args.current[0]})
        print(f"currents: {currents}")

        sim_data = {
            "resource_type": args.mtype,
            "resource_id": ids[args.name],
            "method": args.method,
            "model": args.model,
            "geometry": args.geometry,
            "cooling": args.cooling,
            "static": args.static,
            "non_linear": args.nonlinear,
            "currents": currents,
        }

        simu_id = utils.create_object(
            context.session,
            context.web,
            headers=context.headers,
            mtype="simulation",
            data=sim_data,
            verbose=True,
            debug=context.debug,
        )
        if simu_id is None:
            raise RuntimeError(
                f"failed to create simulation for {args.mtype} {args.name} in run subcommand"
            )

        print("Starting setup...")
        context.session.post(
            f"{context.web}/api/simulations/{simu_id}/run_setup",
            headers=context.headers,
        )

        while True:
            simulation = utils.get_object(
                context.session,
                context.web,
                context.headers,
                simu_id,
                mtype="simulation",
                debug=context.debug,
            )
            if simulation["setup_status"] in ["failed", "done"]:
                break
            sleep(10)

        print(f"Setup done: simulation={simulation}")
        print(f'Setup done: status={simulation["setup_status"]}')
        if simulation["setup_status"] == "failed":
            sys.exit(1)

        setup_arch_id = simulation["setup_output_attachment"]["id"]
        setup_filename = utils.download(
            context.session,
            context.web,
            headers=context.headers,
            attach=setup_arch_id,
            wd=args.wd,
            debug=context.debug,
        )
        print(f"{setup_filename} downloaded")
        print(f'simulation {simulation["id"]} setup done')

        return 0
