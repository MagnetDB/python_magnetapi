"""
Extract flow params from records using a fit
"""


import tempfile
import os
import re

import numpy as np
from scipy import optimize

import json
import pandas as pd
from rich.progress import track
from . import utils

# from txt2csv import load_files
from python_magnetrun.utils.files import concat_files
from python_magnetrun.utils.plots import plot_files
from python_magnetrun.magnetdata import MagnetData
from python_magnetrun.processing.stats import nplateaus


def compute(api_server: str, headers: dict, oid: int, debug: bool = False):
    """
    compute flow_params for a given magnet
    """
    print(f"flow_params.compute: api_server={api_server}, id={oid}")
    cwd = os.getcwd()
    print(f"cwd={cwd}")

    # default value
    # set Imax to 40 kA to enable real Imax detection
    flow_params = {
        "Vp0": {"value": 1000, "unit": "rpm"},
        "Vpmax": {"value": 2840, "unit": "rpm"},
        "F0": {"value": 0, "unit": "l/s"},
        "Fmax": {"value": 61.71612272405876, "unit": "l/s"},
        "Pmax": {"value": 22, "unit": "bar"},
        "Pmin": {"value": 4, "unit": "bar"},
        "Pout": {"value": 4, "unit": "bar"},
        "Imax": {"value": 28000, "unit": "A"},
    }

    Imax = flow_params["Imax"]["value"]  # 28000

    # get magnet type: aka bitter|helix|supra ??
    odata = utils.get_object(
        api_server,
        headers=headers,
        mtype="magnet",
        id=oid,
        debug=debug,
    )
    if debug:
        print(f"magnet data: {json.dumps(odata, indent=2, default=str)}")
    mname = odata["name"]
    mpart = odata["magnet_parts"][0]
    otype = mpart["part"]["type"]
    # print(f"magnet type: {otype}")

    # TODO: change according to magnet type
    # or better store data with RpmH and RpmB
    # similarely keep only Ih, Ib instead of Icoil
    # and Ih_ref, Ib_ref instead of of Iddcct1
    # Iddct are values of measured current
    # Icoil  are actually referenced values required by the user
    fit_data = {
        "M9": {"Rpm": "Rpm1", "Flow": "Flow1", "Pin": "HP1", "Pout": "BP", "rlist": []},
        "M10": {
            "Rpm": "Rpm2",
            "Flow": "Flow2",
            "Pin": "HP2",
            "Pout": "BP",
            "rlist": [],
        },
    }
    if otype == "bitter":
        fit_data = {
            "M9": {
                "Rpm": "Rpm2",
                "Flow": "Flow2",
                "Pin": "HP2",
                "Pout": "BP",
                "rlist": [],
            },
            "M10": {
                "Rpm": "Rpm1",
                "Flow": "Flow1",
                "Pin": "HP1",
                "Pout": "BP",
                "rlist": [],
            },
        }

    sites = utils.get_history(
        api_server, headers, oid, mtype="magnet", otype="site", debug=debug
    )
    if debug:
        print(f"sites: {json.dumps(sites, indent=2, default=str)}")
        for i, site in enumerate(sites):
            print(f"site[{i}/{len(sites)}]: {json.dumps(site, indent=2, default=str)}")

    with tempfile.TemporaryDirectory() as tempdir:
        os.chdir(tempdir)
        if debug:
            print(f"moving to {tempdir}")

        for site in sites:
            sname = site["site"]["name"]
            records = utils.get_history(
                api_server,
                headers,
                site["site_id"],
                mtype="site",
                otype="record",
                verbose=debug,
                debug=debug,
            )

            # download files
            files = []
            total = 0
            nrecords = len(records)
            if debug:
                print(f"site[{site['site']['name']}]: nrecords={nrecords}")

            housing = None
            for i in track(
                range(nrecords),
                description=f"Processing records for site {site['site']['name']}...",
            ):
                f = records[i]
                # print(f'f={f}')
                attach = f["attachment_id"]
                filename = utils.download(
                    api_server, headers, attach, verbose=debug, debug=debug
                )
                housing = filename.split("_")[0]
                files.append(filename)
                total += 1
                if i >= 40:
                    break
            print(f"Processed {total} records.")

            if files:
                # get keys to be extracted
                df = pd.read_csv(files[0], sep=r"\s+", engine="python", skiprows=1)
                # remove columns with zero
                df = df.loc[:, (df != 0.0).any(axis=0)]
                Ikey = "tttt"

                # get first Icoil column (not necessary Icoil1)
                keys = df.columns.values.tolist()
                if debug:
                    print(f"{files[0]}: keys={keys}")

                # key first or latest header that match Icoil\d+ depending on mtype
                Ikeys = []
                for _key in keys:
                    _found = re.match("(Icoil\d+)", _key)
                    if _found:
                        Ikeys.append(_found.group())
                Ikey = Ikeys[0]
                if otype == "bitter":
                    Ikey = Ikeys[-1]
                print(f"Ikey={Ikey}")

                dropped_files = []

                # Imax detection
                xField = (Ikey, "A")
                yField = (fit_data[housing]["Rpm"], "rpm")
                threshold = 2.0e-2
                num_points_threshold = 600

                new_Imax = []
                for file in files:
                    df = pd.read_csv(file, sep=r"\s+", engine="python", skiprows=1)
                    if not Ikey in df.columns.values.tolist():
                        print(f"{Ikey}: no such key in {file} - ignore {file}")
                        dropped_files.append(file)

                    _Rpmmax = df[fit_data[housing]["Rpm"]].max()
                    threshold = _Rpmmax * (1 - 0.1 / 100.0)
                    result = df.query(
                        f'{fit_data[housing]["Rpm"]} >= {threshold} & Field > 0.1'
                    )
                    if not result.empty:
                        """
                        _Istats = result[Ikey].describe(include="all")
                        print(
                            f"Rpmmax={_Rpmmax}, thresold={threshold} {Ikey}: {_Istats}"
                        )

                        import matplotlib.pyplot as plt

                        result.plot.scatter(
                            x=Ikey, y=fit_data[housing]["Rpm"], grid=True
                        )
                        lname = file.replace("_", "-")
                        lname = lname.replace(".txt", "")
                        lname = lname.split("/")
                        plt.title(lname[-1])
                        plt.show()
                        plt.close()
                        """

                        if result[Ikey].std() >= 10:
                            new_Imax.append(result[Ikey].min())

                    """
                    Data = MagnetData.fromtxt(file)
                    plateaus = nplateaus(
                        Data, xField, yField, threshold, num_points_threshold, show=True
                    )
                    if plateaus:
                        new_Imax = {min(plateaus[0]["start"], Imax)}
                        print(f"new_Imax = {new_Imax}")
                    """

                if new_Imax:
                    new_Imax_mean = sum(new_Imax) / len(new_Imax)
                    if Imax != new_Imax_mean:
                        print(f"new_Imax = {new_Imax_mean}")
                        flow_params["Imax"]["value"] = new_Imax_mean
                        Imax = new_Imax_mean

                for file in dropped_files:
                    files.drop(file)

                df = concat_files(
                    files, keys=[Ikey, fit_data[housing]["Rpm"]], debug=debug
                )
                # pairs = [f"{Ikey}-{fit_data[housing]['Rpm']}"]
                # print(f"concat_files: files={files}")
                # print(f"concat_files: keys={df.columns.values.tolist()}")

                def vpump_func(x, a: float, b: float):
                    return a * (x / Imax) ** 2 + b

                df.replace([np.inf, -np.inf], np.nan, inplace=True)
                df.dropna(inplace=True)

                # # drop values for Icoil1 > Imax
                result = df.query(f"{Ikey} <= {Imax}")  # , inplace=True)
                if result is not None and debug:
                    print(f"df: nrows={df.shape[0]}, results: nrows={result.shape[0]}")
                    print(f"result max: {result[Ikey].max()}")

                x_data = result[f"{Ikey}"].to_numpy()
                y_data = result[fit_data[housing]["Rpm"]].to_numpy()
                params, params_covariance = optimize.curve_fit(
                    vpump_func, x_data, y_data
                )

                print("Rpm Fit:")
                print(f"result params: {params}")
                print(f"result covariance: {params_covariance}")
                print(f"result stderr: {np.sqrt(np.diag(params_covariance))}")
                flow_params["Vp0"]["value"] = params[1]
                flow_params["Vpmax"]["value"] = params[0]
                vp0 = flow_params["Vp0"]["value"]
                vpmax = flow_params["Vpmax"]["value"]

                # TODO update interface with name=f'{sname}_{mname}'
                plot_files(
                    f"{sname}-{mname}",
                    files,
                    key1=Ikey,
                    key2=fit_data[housing]["Rpm"],
                    fit=(x_data, [vpump_func(x, vpmax, vp0) for x in x_data]),
                    show=debug,
                    debug=debug,
                    wd=cwd,
                )
                # print(f"plot_files: key1={Ikey}, key2={fit_data[housing]['Rpm']}")

                # Fit for Flow
                df = concat_files(
                    files, keys=[Ikey, fit_data[housing]["Flow"]], debug=debug
                )
                # pairs = [f"{Ikey}-{fit_data[housing]['Flow']}"]
                # print(f"concat_files: files={files}")
                # print(f"concat_files: keys={df.columns.values.tolist()}")

                def flow_func(x, F0: float, Fmax: float):
                    return F0 + Fmax * vpump_func(x, vpmax, vp0) / (vpmax + vp0)

                df.replace([np.inf, -np.inf], np.nan, inplace=True)
                df.dropna(inplace=True)

                # # drop values for Icoil1 > Imax
                result = df.query(f"{Ikey} <= {Imax}")  # , inplace=True)
                if result is not None and debug:
                    print(f"df: nrows={df.shape[0]}, results: nrows={result.shape[0]}")

                y_data = result[fit_data[housing]["Flow"]].to_numpy()
                params, params_covariance = optimize.curve_fit(
                    flow_func, x_data, y_data
                )
                print("Flow Fit:")
                print(f"result params: {params}")
                print(f"result covariance: {params_covariance}")
                print(f"result stderr: {np.sqrt(np.diag(params_covariance))}")
                flow_params["F0"]["value"] = params[0]
                flow_params["Fmax"]["value"] = params[1]
                F0 = flow_params["F0"]["value"]
                Fmax = flow_params["Fmax"]["value"]

                # correlation flow
                plot_files(
                    f"{sname}-{mname}",
                    files,
                    key1=Ikey,
                    key2=fit_data[housing]["Flow"],
                    fit=(x_data, [flow_func(x, F0, Fmax) for x in x_data]),
                    show=debug,
                    debug=debug,
                    wd=cwd,
                )
                # print(f"plot_files: key1={Ikey}, key2={fit_data[housing]['Flow']}")

                # Fit for Pressure
                df = concat_files(
                    files, keys=[Ikey, fit_data[housing]["Pin"]], debug=debug
                )
                # pairs = [f"{Ikey}-{fit_data[housing]['Pin']}"]
                # print(f"concat_files: files={files}")
                # print(f"concat_files: keys={df.columns.values.tolist()}")

                def pressure_func(x, P0: float, Pmax: float):
                    return P0 + Pmax * (vpump_func(x, vpmax, vp0) / (vpmax + vp0)) ** 2

                df.replace([np.inf, -np.inf], np.nan, inplace=True)
                df.dropna(inplace=True)

                # # drop values for Icoil1 > Imax
                result = df.query(f"{Ikey} <= {Imax}")  # , inplace=True)
                if result is not None and debug:
                    print(f"df: nrows={df.shape[0]}, results: nrows={result.shape[0]}")

                y_data = result[fit_data[housing]["Pin"]].to_numpy()
                params, params_covariance = optimize.curve_fit(
                    pressure_func, x_data, y_data
                )
                print("Pressure Fit:")
                print(f"result params: {params}")
                print(f"result covariance: {params_covariance}")
                print(f"result stderr: {np.sqrt(np.diag(params_covariance))}")
                flow_params["Pmin"]["value"] = params[0]
                flow_params["Pmax"]["value"] = params[1]
                P0 = flow_params["Pmin"]["value"]
                Pmax = flow_params["Pmax"]["value"]

                # correlation Pin
                plot_files(
                    f"{sname}-{mname}",
                    files,
                    key1=Ikey,
                    key2=fit_data[housing]["Pin"],
                    fit=(x_data, [pressure_func(x, P0, Pmax) for x in x_data]),
                    show=debug,
                    debug=debug,
                    wd=cwd,
                )
                # print(f"plot_files: key1={Ikey}, key2={fit_data[housing]['Pin']}")

                df = concat_files(
                    files, keys=[Ikey, fit_data[housing]["Pout"]], debug=debug
                )
                mean_Pout = df[fit_data[housing]["Rpm"]].mean()

                # correlation Pout
                plot_files(
                    f"{sname}-{mname}",
                    files,
                    key1=Ikey,
                    key2=fit_data[housing]["Pout"],
                    fit=(x_data, [mean_Pout for x in x_data]),
                    show=debug,
                    debug=debug,
                    wd=cwd,
                )
                # print(f"plot_files: key1={Ikey}, key2={fit_data[housing]['Pout']}")
                flow_params["Pout"]["value"] = mean_Pout

                # save flow_params
                filename = f"{cwd}/{sname}_{mname}-flow_params.json"
                with open(filename, "w") as f:
                    f.write(json.dumps(flow_params, indent=4))

        os.chdir(cwd)
