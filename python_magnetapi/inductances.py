"""
Extract flow params from records using a fit
"""


import tempfile
import sys
import os
import re

import numpy as np
from scipy import optimize

import json
import pandas as pd
from rich.progress import track
from . import utils

from python_magnetsetup.ana import msite_setup, magnet_setup
from python_magnetsetup.config import appenv

# from txt2csv import load_files
from python_magnetrun.MagnetRun import MagnetRun

import MagnetTools.Bmap as bmap
import MagnetTools.MagnetTools as mt


def compute(
    session,
    api_server: str,
    headers: dict,
    oid: int,
    mtype: str = "magnet",
    verbose: bool = False,
    debug: bool = False,
):
    """
    compute inductances for a given magnet or site
    """

    if mtype == "site":
        site = utils.get_object(
            session,
            f"{api_server}",
            headers=headers,
            mtype="site",
            id=oid,
            verbose=verbose,
            debug=debug,
        )
        # print(f"site[{i}]: {sites[i]['name']}")

        # add route to get data in visualisation
        config_data = utils.get_data(
            session, api_server, headers, oid=site["id"], mtype="site", debug=debug
        )

        # create datastruct for Hoop calc
        with tempfile.TemporaryDirectory() as tempdir:
            os.chdir(tempdir)
            data_dir = f"{tempdir}/data"
            os.mkdir(f"{tempdir}/data")
            os.mkdir(f"{tempdir}/data/geometries")
            print(f"moving to {tempdir}")

        env = appenv(
            envfile=None,
            url_api=data_dir,
            yaml_repo=f"{data_dir}/geometries",
            cad_repo=f"{data_dir}/cad",
            mesh_repo=data_dir,
            simage_repo=data_dir,
            mrecord_repo=data_dir,
            optim_repo=data_dir,
        )
        data = msite_setup(env, config_data["results"], debug)

    elif mtype == "magnet":
        magnet = utils.get_object(
            session,
            f"{api_server}",
            headers=headers,
            mtype="magnet",
            id=oid,
            verbose=verbose,
            debug=debug,
        )

        data = magnet_setup(env, config_data["results"], debug)

    else:
        print(f"inductance.compute: expect a magnet or a site - got a {mtype}")
        return None

    (Tubes, Helices, OHelices, BMagnets, UMagnets, Shims) = data
    icurrents = mt.get_currents(Tubes, Helices, BMagnets, UMagnets)

    for i, magnet in enumerate(BMagnets):
        print("Inductance(BMagnet[{i}):", magnet.Inductance(), flush=True)
        if i != len(BMagnets) - 1:
            for j in range(i + 1, len(BMagnets)):
                print(
                    "Inductance(BMagnet[{i}/BMagnet[j}]):",
                    mt.Mutuel(magnet, BMagnets[j]),
                    flush=True,
                )
