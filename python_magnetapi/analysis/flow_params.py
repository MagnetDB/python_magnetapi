"""
Extract flow params from records using a fit.

This module handles data acquisition from the MagnetDB API and delegates
curve fitting to python_magnetcooling.fitting. The separation of concerns is:
  - Data acquisition & record management: this module (python_magnetapi)
  - Curve fitting & hydraulic calculations: python_magnetcooling.fitting
  - WaterFlow object creation: python_magnetcooling.waterflow_factory / fitting.build_waterflow
"""

import tempfile
import os
import re
import datetime
import json
import logging

from math import floor

import numpy as np
import pandas as pd
from rich.progress import track

from .. import utils

from python_magnetrun.utils.files import concat_files
from python_magnetrun.utils.plots import plot_files
from python_magnetrun.magnetdata import MagnetData
from python_magnetrun.processing.stats import nplateaus

from python_magnetcooling.fitting import (
    fit_hydraulic_system,
    build_waterflow,
)
from python_magnetcooling.waterflow_factory import from_flow_params

logger = logging.getLogger(__name__)


def _extract_arrays_from_files(
    files: list,
    Ikey: str,
    rpm_key: str,
    flow_key: str,
    pin_key: str,
    pout_key: str,
    threshold: float,
    debug: bool = False,
) -> dict:
    """
    Extract numpy arrays from record files for fitting.

    Concatenates data from multiple record files, cleans NaN/Inf values,
    and filters by current threshold.

    Parameters
    ----------
    files : list
        List of record file paths.
    Ikey : str
        Column name for current.
    rpm_key, flow_key, pin_key, pout_key : str
        Column names for pump speed, flow rate, inlet pressure, and back pressure.
    threshold : float
        Maximum current value (Imax) for filtering.
    debug : bool
        Enable debug output.

    Returns
    -------
    dict
        Dictionary with numpy arrays: 'current', 'pump_speed', 'flow_rate',
        'pressure', 'back_pressure'.
    """
    all_keys = [Ikey, rpm_key, flow_key, pin_key, pout_key]

    df = concat_files(files, keys=all_keys, debug=debug)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

    # Filter by current threshold
    result = df.query(f"{Ikey} <= {threshold}")
    if result is not None and debug:
        print(f"df: nrows={df.shape[0]}, results: nrows={result.shape[0]}")
        print(f"result max: {result[Ikey].max()}")

    return {
        "current": result[Ikey].to_numpy(),
        "pump_speed": result[rpm_key].to_numpy(),
        "flow_rate": result[flow_key].to_numpy(),
        "pressure": result[pin_key].to_numpy(),
        "back_pressure": result[pout_key].to_numpy(),
    }


def _build_flow_params_dict(pump_fit, flow_pressure_fit) -> dict:
    """
    Build the standard flow_params dictionary from fit results.

    This preserves backward compatibility with code that expects
    the legacy dict format (e.g. for JSON serialization).

    Parameters
    ----------
    pump_fit : PumpSpeedFit
        Pump speed fit results.
    flow_pressure_fit : FlowPressureFit
        Flow rate and pressure fit results.

    Returns
    -------
    dict
        Flow parameters in the standard format with value/unit pairs.
    """
    return {
        "Vp0": {"value": pump_fit.vp0, "unit": "rpm"},
        "Vpmax": {"value": pump_fit.vpmax, "unit": "rpm"},
        "F0": {"value": flow_pressure_fit.f0, "unit": "l/s"},
        "Fmax": {"value": flow_pressure_fit.fmax, "unit": "l/s"},
        "Pmax": {"value": flow_pressure_fit.pmax, "unit": "bar"},
        "Pmin": {"value": flow_pressure_fit.pmin, "unit": "bar"},
        "Pout": {"value": flow_pressure_fit.back_pressure, "unit": "bar"},
        "Imax": {"value": pump_fit.imax, "unit": "A"},
    }


def _detect_imax_from_files(
    files: list,
    Ikey: str,
    rpm_key: str,
    housing: str,
    fit_data: dict,
    Imax: float,
    debug: bool = False,
) -> tuple:
    """
    Detect Imax from plateau regions in record files.

    Examines each record file for plateau regions in pump speed
    to determine the actual maximum operating current.

    Parameters
    ----------
    files : list
        List of record file paths.
    Ikey : str
        Column name for current.
    rpm_key : str
        Column name for pump speed.
    housing : str
        Housing identifier (e.g. 'M9', 'M10').
    fit_data : dict
        Fit data configuration per housing.
    Imax : float
        Current Imax estimate.
    debug : bool
        Enable debug output.

    Returns
    -------
    tuple
        (new_Imax, dropped_files) where new_Imax is the detected Imax
        (or original if no plateau found) and dropped_files is the list
        of files to exclude from fitting.
    """
    new_Imax_values = []
    dropped_files = []

    for file in files:
        _df = pd.read_csv(file, sep=r"\s+", engine="python", skiprows=1)
        if Ikey not in _df.columns.values.tolist():
            print(f"{Ikey}: no such key in {file} - ignore {file}")
            dropped_files.append(file)
        else:
            # Compute duration and drop short records
            if (
                "Date" in _df.columns.values.tolist()
                and "Time" in _df.columns.values.tolist()
            ):
                tformat = "%Y.%m.%d %H:%M:%S"
                t0 = datetime.datetime.strptime(
                    f"{_df['Date'].iloc[0]} {_df['Time'].iloc[0]}", tformat
                )
                _df["t"] = _df.apply(
                    lambda row: (
                        datetime.datetime.strptime(
                            f"{row.Date} {row.Time}", tformat
                        )
                        - t0
                    ).total_seconds(),
                    axis=1,
                )
            duration = _df["t"].iloc[-1] - _df["t"][0]
            if duration <= 15 * 60:
                dropped_files.append(file)
            else:
                # Detect plateau in pump speed
                _Rpmmax = _df[fit_data[housing]["Rpm"]].max()
                threshold = _Rpmmax * (1 - 0.1 / 100.0)
                result = _df.query(
                    f'{fit_data[housing]["Rpm"]} >= {threshold}'
                )
                if not result.empty:
                    if (
                        result[Ikey].std() >= 10
                        and result[Ikey].count() >= 100
                        and result["Field"].max() >= 0.5
                    ):
                        if debug:
                            _Istats = result[Ikey].describe(include="all")
                            print(
                                f'Rpmmax={_Rpmmax}, threshold={threshold} '
                                f'{Ikey}: {_Istats}, Field: {result["Field"].max()}'
                            )
                        new_Imax_values.append(result[Ikey].min())

    # Update Imax if plateaus were detected
    detected_Imax = Imax
    if new_Imax_values:
        new_Imax_mean = sum(new_Imax_values) / len(new_Imax_values)
        if Imax != new_Imax_mean:
            print(f"new_Imax = {new_Imax_mean} raw={new_Imax_values}")
            detected_Imax = new_Imax_mean

    return detected_Imax, dropped_files


def compute(
    session,
    api_server: str,
    headers: dict,
    oid: int,
    samples: int = 20,
    debug: bool = False,
):
    """
    Compute flow_params for a given magnet.

    Fetches record data from MagnetDB API, downloads and processes record files,
    detects Imax from plateau regions, and delegates curve fitting to
    python_magnetcooling.fitting.fit_hydraulic_system().

    The fitted parameters are saved as JSON and a WaterFlow object is returned.

    Parameters
    ----------
    session : requests.Session
        Active HTTP session for API calls.
    api_server : str
        MagnetDB API server URL.
    headers : dict
        HTTP headers (including authorization).
    oid : int
        Magnet object ID in the database.
    samples : int
        Maximum number of records to sample per site (default 20).
    debug : bool
        Enable debug output and plots.

    Returns
    -------
    WaterFlow or None
        Fitted WaterFlow object, or None if no data was available.
    """
    print(f"flow_params.compute: api_server={api_server}, id={oid}")
    cwd = os.getcwd()
    print(f"cwd={cwd}")

    # Default flow parameters (used as initial Imax estimate)
    default_Imax = 28000  # A

    # Get magnet type to determine channel mapping
    odata = utils.get_object(
        session,
        api_server,
        headers=headers,
        mtype="magnet",
        id=oid,
    )
    if debug:
        print(f"magnet data: {json.dumps(odata, indent=2, default=str)}")
    mname = odata["name"]
    mpart = odata["magnet_parts"][0]
    otype = mpart["part"]["type"]

    # Channel mapping depends on magnet type (helix vs bitter)
    # on M9: FlowH = Flow1, FlowB = Flow2
    # on M8,M10: FlowH = Flow2, FlowB = Flow1
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

    # Get sites associated with the magnet
    sites = utils.get_history(
        session, api_server, headers, oid, mtype="magnet", otype="site"
    )
    if debug:
        print(f"sites: {json.dumps(sites, indent=2, default=str)}")
        for i, site in enumerate(sites):
            print(f"site[{i}/{len(sites)}]: {json.dumps(site, indent=2, default=str)}")

    waterflow = None

    with tempfile.TemporaryDirectory() as tempdir:
        os.chdir(tempdir)
        if debug:
            print(f"moving to {tempdir}")

        for site in sites:
            sname = site["site"]["name"]
            records = utils.get_history(
                session,
                api_server,
                headers,
                site["site_id"],
                mtype="site",
                otype="record",
            )

            # Download record files (random sampling if many records)
            files = []
            nrecords = len(records)
            ithreshold = nrecords
            if nrecords > samples:
                ithreshold = min(samples, floor(nrecords * 0.80))
            if debug:
                print(f"site[{sname}]: nrecords={nrecords}")

            housing = None
            import random

            num_records = range(ithreshold)
            if nrecords > 20:
                random.seed()
                num_records = random.sample(range(0, nrecords), ithreshold)
            print(f"randomly selected records ({ithreshold}): {num_records}")

            for i in track(
                range(ithreshold),
                description=f"Processing records for site {sname} (pick {ithreshold}/{nrecords})",
            ):
                f = records[num_records[i]]
                attach = f["attachment_id"]
                filename = utils.download(
                    session, api_server, headers, attach
                )
                housing = filename.split("_")[0]
                files.append(filename)

            if files:
                # Detect the current column key
                df_sample = pd.read_csv(
                    files[0], sep=r"\s+", engine="python", skiprows=1
                )
                df_emptycolumns = df_sample.mask(df_sample != 0).dropna(axis=1)
                keys_emptycolumns = [
                    _key
                    for _key in df_emptycolumns.columns.values.tolist()
                    if re.match(r"Icoil\d+", _key)
                ]
                for _key in ["Icoil15", "Icoil16"]:
                    try:
                        keys_emptycolumns.remove(_key)
                    except ValueError:
                        pass

                keys = df_sample.columns.values.tolist()
                if debug:
                    print(f"{files[0]}: keys={keys}")

                Ikeys = []
                for _key in keys:
                    _found = re.match(r"(Icoil\d+)", _key)
                    if _found and _key not in keys_emptycolumns:
                        Ikeys.append(_found.group())
                Ikey = Ikeys[0]
                if otype == "bitter":
                    Ikey = Ikeys[-1]
                print(f"Ikey={Ikey}")

                # Detect Imax from plateau regions and filter bad files
                Imax, dropped_files = _detect_imax_from_files(
                    files, Ikey, fit_data[housing]["Rpm"],
                    housing, fit_data, default_Imax, debug
                )

                for file in dropped_files:
                    files.remove(file)

                if not files:
                    print(f"No valid files remaining for site {sname}, skipping")
                    continue

                # Extract arrays from record files
                arrays = _extract_arrays_from_files(
                    files,
                    Ikey=Ikey,
                    rpm_key=fit_data[housing]["Rpm"],
                    flow_key=fit_data[housing]["Flow"],
                    pin_key=fit_data[housing]["Pin"],
                    pout_key=fit_data[housing]["Pout"],
                    threshold=Imax,
                    debug=debug,
                )

                # Delegate fitting to python_magnetcooling
                pump_fit, flow_pressure_fit = fit_hydraulic_system(
                    current=arrays["current"],
                    pump_speed=arrays["pump_speed"],
                    flow_rate=arrays["flow_rate"],
                    pressure=arrays["pressure"],
                    back_pressure=arrays["back_pressure"],
                    imax=Imax,
                    method="simple",
                    current_threshold=0.0,  # Already filtered in _extract_arrays_from_files
                )

                # Build WaterFlow object from fit results
                waterflow = build_waterflow(pump_fit, flow_pressure_fit)

                # Build and save flow_params dict (backward compatible JSON format)
                flow_params = _build_flow_params_dict(pump_fit, flow_pressure_fit)
                print(f"flow_params: {json.dumps(flow_params, indent=4)}")

                filename = f"{cwd}/{sname}_{mname}-flow_params.json"
                with open(filename, "w") as f:
                    f.write(json.dumps(flow_params, indent=4))

                # Generate diagnostic plots if debug is enabled
                if debug:
                    plot_files(
                        f"{sname}-{mname}",
                        files,
                        key1=Ikey,
                        key2=fit_data[housing]["Rpm"],
                        fit=None,
                        show=debug,
                        debug=debug,
                        wd=cwd,
                    )

                # Log fit quality
                print(
                    f"Fit results for {sname}/{mname}:\n"
                    f"  Pump speed: Vpmax={pump_fit.vpmax:.2f} rpm, "
                    f"Vp0={pump_fit.vp0:.2f} rpm, "
                    f"R²={pump_fit.fit_result.r_squared:.6f}\n"
                    f"  Flow rate: F0={flow_pressure_fit.f0:.2f} l/s, "
                    f"Fmax={flow_pressure_fit.fmax:.2f} l/s, "
                    f"R²={flow_pressure_fit.flow_fit.r_squared:.6f}\n"
                    f"  Pressure: Pmin={flow_pressure_fit.pmin:.2f} bar, "
                    f"Pmax={flow_pressure_fit.pmax:.2f} bar, "
                    f"R²={flow_pressure_fit.pressure_fit.r_squared:.6f}\n"
                    f"  Back pressure: {flow_pressure_fit.back_pressure:.2f} "
                    f"± {flow_pressure_fit.back_pressure_std:.2f} bar\n"
                    f"  Imax={pump_fit.imax:.0f} A"
                )

        os.chdir(cwd)

    return waterflow
