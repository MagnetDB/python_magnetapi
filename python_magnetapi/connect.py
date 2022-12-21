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

api_server = os.getenv('MAGNETDB_API_SERVER') or "magnetdb-api.grenoble.lncmi.local"
api_key = os.getenv('MAGNETDB_API_KEY')


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--server", help="specify server", type=str, default=api_server)
    parser.add_argument("--port", help="specify port", type=int, default=8000)
    parser.add_argument("--mtype", help="select object type",
                        type=str,
                        choices=['part', 'magnet', 'site', 'record', 'server', 'simulation'],
                        default='magnet')
    parser.add_argument("--name", help="specify an object name", type=str, default="None")
    parser.add_argument("--debug", help="activate debug mode", action='store_true')

    subparsers = parser.add_subparsers(title="commands", dest="command", help='sub-command help')
    parser_list = subparsers.add_parser('list', help='list help')
    parser_view = subparsers.add_parser('view', help='view help')
    parser_create = subparsers.add_parser('create', help='create help')
    parser_run = subparsers.add_parser('run', help='run help')
    parser_compute = subparsers.add_parser('compute', help='compute help')
    parser_post = subparsers.add_parser('process', help='process help')
    # pull data from srv data
    # push data to srv data
    # get object as json???
    
    # list subcommand

    # view subcommand

    # create subcommand

    # run subcommand
    parser_run.add_argument('--geometry', help='select a method', type=str, choices=['Axi', '3D'], default= 'Axi')
    parser_run.add_argument('--static', help="activate static mode", action='store_true')
    parser_run.add_argument('--nonlinear', help="activate non_linear", action='store_true')
    parser_run.add_argument('--method', help='select a method', type=str, default='cfpdes')
    parser_run.add_argument('--model', help='select a model', type=str, default='thmagel_hcurl')
    parser_run.add_argument('--cooling', help='select a cooling mode', type=str, choices=['mean', 'meanH', 'grad', 'gradH'], default= 'meanH')
    parser_run.add_argument('--setup', help="activate setup only", action='store_true')
    parser_run.add_argument("--compute_server", help="choose compute node", type=str, default='calcul22')
    parser_run.add_argument("--np", help="choose number of procs", type=int, default=4)

    # stats subcommand
    # compute
    parser_compute.add_argument("--flow_params", help="activate flow params", action='store_true')

    # get args
    args = parser.parse_args()

    # main
    otype = args.mtype
    payload = {}
    headers = {'Authorization': os.getenv('MAGNETDB_API_KEY')}
    web = f"http://{args.server}:{args.port}"
    api = f"{web}/api"

    with requests.Session() as s:
        r = s.get(f"{api}/{otype}s", headers=headers)
        response = r.json()
        if args.debug:
            print(f'response={response}')
        if 'detail' in response and response['detail'] == 'Forbidden.':
            raise RuntimeError(f"{args.server} : wrong credentials - check MAGNETDB_API_KEY")

        if args.command == 'list':
            ids = utils.getlist(f"{web}", headers=headers, mtype=otype, debug=args.debug)
            print(f'{args.mtype.upper()}: found {len([*ids])} items')
            for obj in ids:
                print(f'{args.mtype.upper()}: {obj}, id={ids[obj]}')

        if args.command == 'view':
            # add a filter for view
            ids = utils.getlist(f"{web}", headers=headers, mtype=otype, debug=args.debug)
            if args.name in ids:
                response = utils.getobject(f"{web}", headers=headers, mtype=otype, id=ids[args.name], debug=args.debug)
                print(f'{args.name}:\n{json.dumps(response, indent=4)}')
            else:
                raise RuntimeError(f"{args.server} : cannot found {args.name} in {args.mtype.upper()} objects")

        if args.command == 'create':
            # if server, try to guess some values by running appropriate commands on the server
            # if part|magnet|site need to attach some extra files
            # if part|magnet|site update associative tables
            # if record upload file to minio
            print('create: not implemented')

        if args.command == 'run':
            ids = utils.getlist(f"{web}", headers=headers, mtype=otype, debug=args.debug)
            if args.name in ids:
                response = utils.getobject(f"{web}", headers=headers, mtype=otype, id=ids[args.name], debug=args.debug)
            else:
                raise RuntimeError(f"{args.server} : cannot found {args.name} in {args.mtype.upper()} objects")

            if otype not in ['site', 'magnet']:
                raise RuntimeError(f"unexpected type {args.mtype} in run subcommand")

            # TODO: add flow_params
            # use flow_params from magnetsetup if no records attached to object id
            # otherwise try to get flow_params from db or create it
            sim_data={
                'resource_type': args.mtype,
                'resource_id': ids[args.name],
                'method': args.method,
                'model': args.model,
                'geometry': args.geometry,
                'cooling': args.cooling,
                'static': args.static,
                'non_linear': args.nonlinear
            }

            # check parameters consistency: see allowed_methods in
            # create simu
            simu_id = utils.createobject(f"{api}/simulations", headers=headers, mtype='simulation', data=sim_data, debug=args.debug)

            # run setup
            print("Starting setup...")
            r = requests.post(f"{api}/simulations/{simu_id}/run_setup", headers=headers)

            while True:
                simulation = utils.getobject(f"{web}", headers=headers, mtype='simulation', id=simu_id, debug=args.debug)
                if simulation['setup_status'] in ['failed', 'done']:
                    break
                sleep(10)

            print(f"Setup done: status={simulation['set_status']}")
            if simulation['setup_status'] == 'failed':
                sys.exit(1)

            if not args.setup:
                # Run simu with ssh
                ids = utils.getlist(f"{web}", headers=headers, mtype='server', debug=args.debug)
                if args.compute_server in ids:
                    server_id = ids[args.compute_server]
                else:
                    raise RuntimeError(f"{args.server} : cannot found {args.name} in server objects")

                # TODO get server data - aka np
                server_data =  utils.getobject(f"{web}", headers=headers, mtype='server', id=server_id, debug=args.debug)

                print("Starting simulation...")
                r = requests.post(f"{api}/simulations/{simu_id}/run", data={'server_id': server_id}, headers=headers)
                while True:
                    simulation = utils.getobject(f"{web}", headers=headers, mtype='simulation', id=simu_id, debug=args.debug)
                    if simulation['status'] in ['failed', 'done']:
                        break
                    sleep(10)
                print(f"Simulation done: status={simulation['status']}")

                if simulation['status'] == 'failed':
                    sys.exit(1)

        if args.command == 'compute':
            if args.flow_params:
                if otype not in ['site', 'magnet']:
                    raise RuntimeError(f"unexpected type {args.mtype} in compute subcommand flow_params")

                ids = utils.getlist(f"{web}", headers=headers, mtype=otype, debug=args.debug)
                if args.name in ids:
                    response = utils.getobject(f"{web}", headers=headers, mtype=otype, id=ids[args.name], debug=args.debug)
                    from . import flow_params
                    flow_params.compute(f"{web}", headers=headers, mtype=otype, oid=ids[args.name], debug=args.debug)
                else:
                    raise RuntimeError(f"{args.server} : cannot found {args.name} in {args.mtype.upper()} objects")

        if args.command == 'post':
            print('post: not implemented')

if __name__ == "__main__":
    main()
