#! /usr/bin/python3

"""
Connect to MagnetDB site
"""

import os
import sys
import json
import argparse
from time import sleep
import requests
import requests.exceptions

from . import utils

api_server = os.getenv("MAGNETDB_API_SERVER") or "magnetdb-api.lncmig.local"
api_key = os.getenv("MAGNETDB_API_KEY")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", help="specify server", type=str, default=api_server)
    parser.add_argument("--port", help="specify port", type=int, default=8000)
    parser.add_argument("--debug", help="activate debug mode", action="store_true")
    parser.add_argument("--https", help="activate https mode", action="store_true")

    subparsers = parser.add_subparsers(
        title="commands", dest="command", help="sub-command help"
    )
    parser_list = subparsers.add_parser("list", help="list help")
    parser_view = subparsers.add_parser("view", help="view help")
    parser_create = subparsers.add_parser("create", help="create help")
    parser_delete = subparsers.add_parser("delete", help="create help")

    parser_setup = subparsers.add_parser("setup", help="setup help")
    parser_run = subparsers.add_parser("run", help="run help")
    parser_compute = subparsers.add_parser("compute", help="compute help")
    parser_post = subparsers.add_parser("process", help="process help")
    # pull data from srv data
    # push data to srv data
    # get object as json???

    # list subcommand
    parser_list.add_argument(
        "--mtype",
        help="select object type",
        type=str,
        choices=[
            "material",
            "part",
            "magnet",
            "site",
            "record",
            "server",
            "simulation",
        ],
        default="magnet",
    )

    # view subcommand
    parser_view.add_argument(
        "--mtype",
        help="select object type",
        type=str,
        choices=[
            "material",
            "part",
            "magnet",
            "site",
            "record",
            "server",
            "simulation",
        ],
        default="magnet",
    )
    parser_view.add_argument(
        "--name", help="specify an object name", type=str, default="None"
    )

    # create subcommand
    parser_create.add_argument(
        "--mtype",
        help="select object type",
        type=str,
        choices=[
            "material",
            "part",
            "magnet",
            "site",
            "record",
            "server",
            "simulation",
        ],
        default="magnet",
    )
    # parser_create.add_argument("--data", help="specify data as dict", type=json.loads)
    # parser_create.add_argument("--file", help="specify data as file", type=str)
    command_group = parser_create.add_mutually_exclusive_group()
    command_group.add_argument(
        "--data", help="load data from dict", type=json.loads, nargs="?"
    )
    command_group.add_argument(
        "--file", help="load data from file", type=str, nargs="?"
    )

    # delete subcommand
    parser_delete.add_argument(
        "--mtype",
        help="select object type",
        type=str,
        choices=[
            "material",
            "part",
            "magnet",
            "site",
            "record",
            "server",
            "simulation",
        ],
        default="magnet",
    )
    parser_delete.add_argument(
        "--name", help="specify an object name", type=str, default="None"
    )

    # setup subcommand
    parser_setup.add_argument(
        "--mtype",
        help="select object type",
        type=str,
        choices=[
            "magnet",
            "site",
        ],
        default="magnet",
    )
    parser_setup.add_argument(
        "--name", help="specify an object name", type=str, default="None"
    )
    parser_setup.add_argument(
        "--current",
        help="specify requested current (default: 31kA)",
        nargs="+",
        metavar="Current",
        type=float,
        default=[31.0e3],
    )

    parser_setup.add_argument(
        "--geometry",
        help="select a method",
        type=str,
        choices=["Axi", "3D"],
        default="Axi",
    )
    parser_setup.add_argument(
        "--static", help="activate static mode", action="store_true"
    )
    parser_setup.add_argument(
        "--nonlinear", help="activate non_linear", action="store_true"
    )
    parser_setup.add_argument(
        "--method", help="select a method", type=str, default="cfpdes"
    )
    parser_setup.add_argument(
        "--model", help="select a model", type=str, default="thmagel_hcurl"
    )
    parser_setup.add_argument(
        "--cooling",
        help="select a cooling mode",
        type=str,
        choices=["mean", "meanH", "grad", "gradH"],
        default="meanH",
    )
    parser_setup.add_argument(
        "--wd",
        help="select directory to store setup/sumalation results",
        type=str,
        default=".",
    )

    # run subcommand
    parser_run.add_argument(
        "--mtype",
        help="select object type",
        type=str,
        choices=[
            "magnet",
            "site",
        ],
        default="magnet",
    )
    parser_run.add_argument(
        "--simu_id", help="select simulation id", type=int, default=-1
    )
    parser_run.add_argument(
        "--wd",
        help="select directory to store setup/simulation results",
        type=str,
        default=".",
    )

    parser_run.add_argument(
        "--compute_server", help="choose compute node", type=str, default="calcul22"
    )
    parser_run.add_argument("--np", help="choose number of procs", type=int, default=4)

    # stats subcommand
    # compute
    parser_compute.add_argument(
        "--mtype",
        help="select object type",
        type=str,
        choices=[
            "part",
            "magnet",
            "site",
            "record",
        ],
        default="magnet",
    )
    parser_compute.add_argument(
        "--name", help="specify an object name", type=str, default="None"
    )
    parser_compute.add_argument(
        "--flow_params", help="activate flow params", action="store_true"
    )
    parser_compute.add_argument(
        "--hoop_stress", help="activate hoop stress history", action="store_true"
    )

    # get args
    args = parser.parse_args()

    # main
    otype = args.mtype
    payload = {}
    headers = {"Authorization": os.getenv("MAGNETDB_API_KEY")}
    web = f"http://{args.server}:{args.port}"
    if args.https:
        web = f"https://{args.server}"

    with requests.Session() as s:
        r = s.get(f"{web}/api/{otype}s", headers=headers, verify=True)
        print(f"r={r}")
        response = r.json()
        # print(f"response={response}")
        if args.debug:
            print(f"response={response}")
        if "detail" in response and response["detail"] == "Forbidden.":
            raise RuntimeError(
                f"{args.server} : wrong credentials - check MAGNETDB_API_KEY"
            )

        if args.command == "list":
            ids = utils.get_list(web, headers=headers, mtype=otype, debug=args.debug)
            print(f"{args.mtype.upper()}: found {len([*ids])} items")
            for obj in ids:
                print(f"{args.mtype.upper()}: {obj}, id={ids[obj]}")

        if args.command == "view":
            # add a filter for view
            ids = utils.get_list(web, headers=headers, mtype=otype, debug=args.debug)
            print(f"view: ids={ids}")
            if args.name in ids:
                response = utils.get_object(
                    web,
                    headers=headers,
                    mtype=otype,
                    id=ids[args.name],
                    debug=args.debug,
                )
                print(f"{args.name}:\n{json.dumps(response, indent=4)}")
            else:
                raise RuntimeError(
                    f"{args.server} : cannot found {args.name} in {args.mtype.upper()} objects"
                )

        if args.command == "create":
            # if server, try to guess some values by running appropriate commands on the server
            # if part|magnet|site need to attach some extra files and upload then to minio
            # if part|magnet|site update associative tables
            # if record upload file to minio

            data = {}
            if args.data:
                print(f"create: data={json.dumps(args.data, indent=4, default=str)}")
                data = args.data
                # how to validate data
            if args.file:
                print(f"create: file={args.file}")
                with open(args.file, "r") as f:
                    data = json.loads(f.read())
                    print(f"data: {data}")

            from .material import create as mat_create
            from .site import create as site_create
            from .magnet import create as magnet_create
            from .part import create as part_create
            from .record import create as record_create

            ocreate = {
                "material": mat_create,
                "site": site_create,
                "magnet": magnet_create,
                "part": part_create,
                "record": record_create,
            }

            id = ocreate[otype](
                web, headers=headers, data=data, verbose=True, debug=args.debug
            )

            # create material if not already done then part
            if id is None:
                print(f"create: type={otype}, name={data['name']} not implemented")

        if args.command == "delete":
            ids = utils.get_list(web, headers=headers, mtype=otype, debug=args.debug)
            if args.name in ids:
                print(f"{args.name}: id={ids[args.name]}")
                response = utils.del_object(
                    web,
                    headers=headers,
                    mtype=otype,
                    id=ids[args.name],
                    verbose=True,
                    debug=args.debug,
                )
            else:
                raise RuntimeError(
                    f"{args.server} : cannot found {args.name} in {args.mtype.upper()} objects"
                )

        if args.command == "setup":
            if otype not in ["site", "magnet"]:
                raise RuntimeError(
                    f"unexpected type {args.mtype} in run subcommand - expect mtype=site|magnet"
                )

            ids = utils.get_list(web, headers=headers, mtype=otype, debug=args.debug)
            if args.name in ids:
                response = utils.get_object(
                    web,
                    headers=headers,
                    mtype=otype,
                    id=ids[args.name],
                    debug=args.debug,
                )
            else:
                raise RuntimeError(
                    f"run: cannot found {args.name} in {args.mtype.upper()} objects"
                )

            # TODO: add flow_params
            # use flow_params from magnetsetup if no records attached to object id
            # otherwise try to get flow_params from db or create it
            # TODO:  add current_data
            # currents: List[CreatePayloadCurrent]
            # with CreatePayloadCurrent(BaseModel): magnet_id: int, value: float
            object = utils.get_object(
                web,
                headers,
                ids[args.name],
                mtype=otype,
                verbose=True,
                debug=args.debug,
            )

            currents = []
            if otype == "site":
                if len(args.current) != len(object["site_magnets"]):
                    raise RuntimeError(
                        f"args.current contains {len(args.current)} values - should have {len(object['site_magnets'])} values"
                    )

                for i, magnet in enumerate(object["site_magnets"]):
                    print(f"current[{i}]: magnet={magnet}")
                    current_data = {
                        "magnet_id": magnet["magnet_id"],
                        "value": args.current[i],
                    }
                    currents.append(current_data)
            else:
                if len(args.current) != 1:
                    raise RuntimeError(
                        f"args.current contains {len(args.current)} values - should have 1 value"
                    )

                current_data = {
                    "magnet_id": ids[args.name],
                    "value": args.current[0],
                }
                currents.append(current_data)
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

            # check parameters consistency: see allowed_methods in
            # create simu
            simu_id = utils.create_object(
                web,
                headers=headers,
                mtype="simulation",
                data=sim_data,
                verbose=True,
                debug=args.debug,
            )
            if simu_id is None:
                raise RuntimeError(
                    f"failed to create simulation for {args.mtype} {args.name} in run subcommand"
                )

            # run setup
            print("Starting setup...")
            r = requests.post(
                f"{web}/api/simulations/{simu_id}/run_setup", headers=headers
            )

            while True:
                simulation = utils.get_object(
                    web,
                    headers=headers,
                    mtype="simulation",
                    id=simu_id,
                    debug=args.debug,
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
                web,
                headers=headers,
                attach=setup_arch_id,
                wd=args.wd,
                debug=args.debug,
            )
            print(f"{setup_filename} downloaded")
            print(f'simulation {simulation["id"]} setup done')

        if args.command == "run":
            # find simu_id
            simu = utils.get_object(
                web,
                headers=headers,
                id=args.simu_id,
                mtype="simulation",
                debug=args.debug,
            )
            if simu is None:
                raise RuntimeError(
                    f"run : cannot find {args.simu_id} simulation - please check simulations list"
                )

            # Run simu with ssh
            ids = utils.get_list(web, headers=headers, mtype="server", debug=args.debug)
            if args.compute_server in ids:
                server_id = ids[args.compute_server]
            else:
                raise RuntimeError(
                    f"{args.server} : cannot found {args.name} in server objects"
                )

            # TODO get server data - aka np
            server_data = utils.get_object(
                web,
                headers=headers,
                mtype="server",
                id=server_id,
                debug=args.debug,
            )

            print("Starting simulation...")
            r = requests.post(
                f"{web}/api/simulations/{args.simu_id}/run",
                data={"server_id": server_id},
                headers=headers,
            )
            while True:
                simulation = utils.get_object(
                    web,
                    headers=headers,
                    mtype="simulation",
                    id=simu_id,
                    debug=args.debug,
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
                web,
                headers=headers,
                attach=simu_arch_id,
                wd=args.wd,
                debug=args.debug,
            )
            print(f"{simu_filename} downloaded")
            print(f'simulation {simulation["id"]} done')

        if args.command == "compute":
            if args.flow_params:
                if otype != "magnet":
                    raise RuntimeError(
                        f"unexpected type {args.mtype} in compute subcommand flow_params - should be magnet"
                    )

                ids = utils.get_list(
                    web, headers=headers, mtype=otype, debug=args.debug
                )
                if args.name in ids:
                    response = utils.get_object(
                        web,
                        headers=headers,
                        mtype=otype,
                        id=ids[args.name],
                        debug=args.debug,
                    )
                    from . import flow_params

                    flow_params.compute(
                        web,
                        headers=headers,
                        oid=ids[args.name],
                        debug=args.debug,
                    )
                else:
                    raise RuntimeError(
                        f"{args.server} : cannot found {args.name} in {args.mtype.upper()} objects"
                    )

            if args.hoop_stress:
                if otype not in ["part"]:
                    raise RuntimeError(
                        f"unexpected type {args.mtype} in compute subcommand hoop_stress"
                    )

                ids = utils.get_list(
                    web, headers=headers, mtype=otype, debug=args.debug
                )
                if args.name in ids:
                    response = utils.get_object(
                        web,
                        headers=headers,
                        mtype=otype,
                        id=ids[args.name],
                        debug=args.debug,
                    )
                    from . import hoop_stress

                    hoop_stress.compute(
                        web,
                        headers=headers,
                        mtype=otype,
                        oid=ids[args.name],
                        debug=args.debug,
                    )
                else:
                    raise RuntimeError(
                        f"{args.server} : cannot found {args.name} in {args.mtype.upper()} objects"
                    )

        if args.command == "post":
            print("post: not implemented")


if __name__ == "__main__":
    main()
