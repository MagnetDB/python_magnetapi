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

from python_magnetsetup.ana import msite_setup
from python_magnetsetup.config import appenv

# from txt2csv import load_files
from python_magnetrun.MagnetRun import MagnetRun

import magnettools.Bmap as bmap
import magnettools.magnettools as mt


def compute(
    session,
    api_server: str,
    headers: dict,
    oid: int,
    mtype: str = "part",
    verbose: bool = False,
    debug: bool = False,
):
    """
    compute hoop stress for a given part
    """
    if mtype != "part":
        print(f"hoop_stress.compute: expect a part - got a {mtype}")
        return None

    part = utils.get_object(
        session,
        f"{api_server}",
        headers=headers,
        mtype="part",
        id=oid,
        verbose=verbose,
        debug=debug,
    )
    if debug:
        print(f"part: {part}")
    part_type = part["type"]
    if part["type"] == "helix":
        mpart = "H"
    elif part["type"] == "bitter":
        mpart = "B"
    elif part["type"] == "supra":
        mpart = "S"
    else:
        print(
            f"hoop_stress.compute: expect a part of type (helix|bitter|supra) - got a {part_type} for part={part['name']}"
        )
        return None

    print(
        f"hoop_stress.compute: api_server={api_server}, mtype={mtype}, otype='site', id={oid}, name={part['name']}"
    )
    cwd = os.getcwd()
    print(f"cwd={cwd}")

    sites = utils.get_history(
        session, api_server, headers, oid, mtype=mtype, otype="site", debug=debug
    )
    if debug:
        print(f"sites: {sites}")

    with tempfile.TemporaryDirectory() as tempdir:
        os.chdir(tempdir)
        data_dir = f"{tempdir}/data"
        os.mkdir(f"{tempdir}/data")
        os.mkdir(f"{tempdir}/data/geometries")
        print(f"moving to {tempdir}")

        nsites = len(sites)
        print(f"Processing sites for part {part['name']}...")
        for i in range(
            nsites
        ):  # track(range(nsites), description=f"Processing sites for part {part['name']}..."):
            # get site with records
            site = utils.get_object(
                session,
                f"{api_server}",
                headers=headers,
                mtype="site",
                id=sites[i]["id"],
                verbose=verbose,
                debug=debug,
            )
            # print(f"site[{i}]: {sites[i]['name']}")

            # add route to get data in visualisation
            config_data = utils.get_data(
                session, api_server, headers, oid=site["id"], mtype="site", debug=debug
            )

            # create datastruct for Hoop calc
            # pname: dict to hold partname <-> Hn or Bn or Sn
            pnames = dict()
            for magnet in site["site_magnets"]:
                _id = magnet["magnet_id"]
                _object = utils.get_object(
                    session,
                    f"{api_server}",
                    headers=headers,
                    mtype="magnet",
                    id=_id,
                    verbose=verbose,
                    debug=debug,
                )
                # print(f"magnet: {_object}")
                geom_data = _object["geometry"]
                yamlfile = geom_data["filename"]
                attach = geom_data["id"]
                filename = utils.download(
                    session,
                    api_server,
                    headers,
                    attach,
                    wd=f"{tempdir}/data/geometries",
                    debug=debug,
                )
                # print(f"magnet: {_object['name']} {yamlfile}")
                num = 0
                for part in _object["magnet_parts"]:
                    _pid = part["part_id"]
                    _ptype = part["part"]["type"]
                    if _ptype in ["helix", "bitter", "supra"]:
                        _pobject = utils.get_object(
                            session,
                            f"{api_server}",
                            headers=headers,
                            mtype="part",
                            id=_pid,
                            verbose=verbose,
                            debug=debug,
                        )
                        # print(f"part: {_pobject}")
                        geom_data = _pobject["geometries"][0]
                        yamlfile = geom_data["attachment"]["filename"]
                        attach = geom_data["attachment"]["id"]
                        filename = utils.download(
                            session,
                            api_server,
                            headers,
                            attach,
                            wd=f"{tempdir}/data/geometries",
                            debug=debug,
                        )
                        print(
                            f"part: {_pobject['name']} {yamlfile} {_ptype.upper()[0]}{num+1}"
                        )
                        pnames[_pobject["name"]] = f"{_ptype.upper()[0]}{num+1}"
                        num += 1

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
            site_data = msite_setup(env, config_data["results"], debug)
            (Tubes, Helices, OHelices, BMagnets, UMagnets, Shims) = site_data
            icurrents = mt.get_currents(Tubes, Helices, BMagnets, UMagnets)

            mdata = {"H": Helices, "B": BMagnets}
            if len(icurrents) == 3:
                mdata["S"] = UMagnets

            # get record data
            total = 0
            # records = utils.get_history(session, api_server, headers, site['site_id'], mtype='site', otype='record', verbose=debug, debug=debug) #site_obj['records']
            nrecords = len(site["records"])
            for j in track(
                range(nrecords),
                description=f"Processing records for site id={site['name']}...",
            ):
                f = site["records"][j]
                # print(f'f={f}')
                attach = f["attachment_id"]
                filename = utils.download(session, api_server, headers, attach, debug)
                housing = filename.split("_")[0]
                if filename.endswith(".txt"):
                    rundata = MagnetRun.fromtxt(housing, site["name"], filename)
                else:
                    rundata = MagnetRun.fromcsv(housing, site["name"], filename)
                total += 1

                # extract timestamp, currents from rundata
                df = rundata.MagnetData.Data[["timestamp", "Field", "IH_ref", "IB_ref"]]
                # print(f'df: {df}')

                """
                def Hoopstress(row):
                    # update Ih, Ib, Is range
                    vcurrents = list(icurrents)
                    num = 0
                    if len(Tubes) != 0: vcurrents[num] = row.IH_ref; num += 1
                    if len(BMagnets) != 0: vcurrents[num] = row.IB_ref; num += 1
                    if len(UMagnets) != 0: vcurrents[num] = 0; num += 1

                    currents = mt.DoubleVector(vcurrents)
                    mt.set_currents(Tubes, Helices, BMagnets, UMagnets, OHelices, currents)

                    for magnet_type in mdata:
                        Magnets = mdata[magnet_type]
                        (headers, values) = bmap.getHoop(Magnets, Tubes, Helices, BMagnets, UMagnets, magnet_type)
                        _df = pd.DataFrame.from_records(values)
                        _df.columns = headers
                        vheaders = _df['num'].tolist()
                        values = _df['Hoop[MPa]'].to_numpy()
                        print(f"_df = {vheaders}, {values}")
                        for k,vheader in enumerate(vheaders):
                            row.vheader = values[k]

                df.apply(lambda row: Hoopstress(row), axis=1)
                print(f'df: {df}')
                """

                data = dict()
                for magnet_type in mdata:
                    Magnets = mdata[magnet_type]
                    (headers, values) = bmap.getHoop(
                        Magnets, Tubes, Helices, BMagnets, UMagnets, magnet_type
                    )
                    _df = pd.DataFrame.from_records(values)
                    _df.columns = headers
                    vheaders = _df["num"].tolist()
                    for k, vheader in enumerate(vheaders):
                        data[vheader] = []

                for _ih, _ib in zip(df["IH_ref"].to_numpy(), df["IB_ref"].to_numpy()):
                    # print(f"Ih={_ih}, Ib={_ib}")
                    # update Ih, Ib, Is range
                    vcurrents = list(icurrents)
                    num = 0
                    if len(Tubes) != 0:
                        vcurrents[num] = _ih
                        num += 1
                    if len(BMagnets) != 0:
                        vcurrents[num] = _ib
                        num += 1
                    if len(UMagnets) != 0:
                        vcurrents[num] = 0
                        num += 1

                    currents = mt.DoubleVector(vcurrents)
                    mt.set_currents(
                        Tubes, Helices, BMagnets, UMagnets, OHelices, currents
                    )

                    for magnet_type in mdata:
                        Magnets = mdata[magnet_type]
                        (headers, values) = bmap.getHoop(
                            Magnets, Tubes, Helices, BMagnets, UMagnets, magnet_type
                        )
                        _df = pd.DataFrame.from_records(values)
                        _df.columns = headers
                        vheaders = _df["num"].tolist()
                        values = _df["Hoop[MPa]"].to_numpy()
                        # print(f"_df = {vheaders}, {values}")
                        for k, vheader in enumerate(vheaders):
                            data[vheader].append(values[i])

                for key in data:
                    df.insert(2, key, data[vheader], True)
                print(f"df: {df}")

                # add plot
                sys.exit(1)
            print(f"Processed {total} records for {site['name']}.")
        os.chdir(cwd)
