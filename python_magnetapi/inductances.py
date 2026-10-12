"""
Extract flow params from records using a fit
"""


import os
import tempfile

import magnettools.magnettools as mt

# from txt2csv import load_files
from python_magnetsetup.ana import magnet_setup, msite_setup
from python_magnetsetup.config import appenv

from . import utils


def compute(
    session,
    api_server: str,
    headers: dict,
    oid: int,
    mtype: str = "magnet",
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
        )
        # print(f"site[{i}]: {sites[i]['name']}")

        # add route to get data in visualisation
        config_data = utils.get_data(
            session, api_server, headers, oid=site["id"], mtype="site"
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
