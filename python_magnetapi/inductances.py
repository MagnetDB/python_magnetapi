"""
Compute self and mutual inductances of a magnet or a site
"""

import logging
import os
import re
import tempfile

import requests
from rich.console import Console
from rich.table import Table

from . import utils

logger = logging.getLogger(__name__)

# older versions skip the last helix of each tube in compute_inductance_matrix
MIN_MAGNETTOOLS = (1, 2, 2)

# (label prefix, group name, self-inductance key)
GROUPS = (("H", "Helix", "L_H"), ("B", "Bitter", "L_B"), ("S", "Supra", "L_S"))
MUTUALS = {("H", "B"): "M_HB", ("H", "S"): "M_HS", ("B", "S"): "M_BS"}

# larger matrices do not fit in a terminal: use csvfile to get them
MAX_PRINTED_SIZE = 6


def _import_magnettools():
    """Import the optional magnettools and python_magnetsetup dependencies.

    Raises:
        RuntimeError: if they are missing or magnettools is too old.
    """
    try:
        import magnettools
        from magnettools.Mutual import compute_inductance_matrix
        from python_magnetsetup.ana import magnet_setup, msite_setup
        from python_magnetsetup.config import appenv
    except ImportError as e:
        raise RuntimeError(
            "inductances need the optional dependencies, "
            f"install python-magnetapi[full]: {e}"
        ) from e

    version = tuple(int(v) for v in re.findall(r"\d+", magnettools.__version__)[:3])
    if version < MIN_MAGNETTOOLS:
        raise RuntimeError(
            f"magnettools>={'.'.join(map(str, MIN_MAGNETTOOLS))} is required, "
            f"found {magnettools.__version__}"
        )
    return compute_inductance_matrix, magnet_setup, msite_setup, appenv


def _download_text(session: requests.Session, url: str, headers: dict, path: str) -> bool:
    """Save the text returned by url to path; return False if there is none."""
    r = session.get(url, headers=headers)
    if r.status_code != 200 or not r.text.strip():
        logger.warning(f"inductances: nothing to save from {url} (status={r.status_code})")
        return False
    with open(path, "w") as f:
        f.write(r.text)
    return True


def _fetch_geometries(
    session: requests.Session,
    api_server: str,
    headers: dict,
    magnets: list[dict],
    data_dir: str,
) -> None:
    """Download what magnet_setup needs for each magnet into data_dir.

    Mirrors generate_magnet_directory on the server:
    - data/geometries/<magnet name>.yaml and <part name>.yaml
    - data/cad/<modelaxi and shape attachments of the parts>
    """
    geom_dir = os.path.join(data_dir, "geometries")
    cad_dir = os.path.join(data_dir, "cad")

    for magnet in magnets:
        _download_text(
            session,
            f"{api_server}/api/magnets/{magnet['id']}/geometry.yaml",
            headers,
            os.path.join(geom_dir, f"{magnet['name']}.yaml"),
        )
        for part in utils.get_parts_for_magnet(session, api_server, headers, magnet["id"]):
            _download_text(
                session,
                f"{api_server}/api/parts/{part['id']}/geometry.yaml",
                headers,
                os.path.join(geom_dir, f"{part['name']}.yaml"),
            )
            for field in ("modelaxi_attachment", "shape_attachment"):
                attach_id = utils.get_fk_id(part, field)
                if attach_id is not None:
                    utils.download(session, api_server, headers, str(attach_id), wd=cad_dir)


def _print_result(name: str, result: dict) -> None:
    """Print the Helix/Bitter/Supra block matrix, and the full matrix if it is small."""
    console = Console()
    labels = result["labels"]

    present = [g for g in GROUPS if any(label.startswith(f"{g[0]}_") for label in labels)]
    blocks = Table(title=f"{name}: inductances [H]")
    blocks.add_column("")
    for _, group, _ in present:
        blocks.add_column(group, justify="right")
    for i, (gi, group, self_key) in enumerate(present):
        row = []
        for j, (gj, _, _) in enumerate(present):
            if i == j:
                value = result[self_key]
            else:
                value = result[MUTUALS.get((gi, gj)) or MUTUALS[(gj, gi)]]
            row.append(f"{value:.6e}")
        blocks.add_row(group, *row)
    console.print(blocks)

    if len(labels) > MAX_PRINTED_SIZE:
        console.print(
            f"full {len(labels)}x{len(labels)} matrix ({', '.join(labels)}): "
            "save it with --csv"
        )
        return

    matrix = Table(title=f"{name}: inductance matrix [H]")
    matrix.add_column("")
    for label in labels:
        matrix.add_column(label, justify="right")
    for label, row in zip(labels, result["matrix"], strict=True):
        matrix.add_row(label, *(f"{value:.6e}" for value in row))
    console.print(matrix)


def compute(
    session: requests.Session,
    api_server: str,
    headers: dict,
    oid: int,
    mtype: str = "magnet",
    debug: bool = False,
    csvfile: str | None = None,
) -> dict | None:
    """Compute self and mutual inductances for a magnet or a site.

    Helix tubes, Bitter magnets and supra magnets are all taken into account
    (see magnettools.Mutual.compute_inductance_matrix).

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        oid: magnet or site ID
        mtype: "magnet" or "site"
        debug: forwarded to python_magnetsetup
        csvfile: optional path to save the inductance matrix as CSV

    Returns:
        dict with "labels", "matrix" (N×N, in H) and the totals
        L_H, L_B, L_S, M_HB, M_HS, M_BS, or None on error.

    Raises:
        RuntimeError: if magnettools/python_magnetsetup are missing or too old.
    """
    if mtype not in ("magnet", "site"):
        print(f"inductances.compute: expect a magnet or a site - got a {mtype}")
        return None

    compute_inductance_matrix, magnet_setup, msite_setup, appenv = _import_magnettools()

    obj = utils.get_object(session, api_server, headers, oid, mtype=mtype)
    if obj is None:
        print(f"inductances.compute: {mtype} id={oid} not found")
        return None

    config_data = utils.get_data(session, api_server, headers, oid=oid, mtype=mtype)
    if config_data is None:
        print(f"inductances.compute: no configuration data for {mtype} {obj['name']}")
        return None

    if mtype == "magnet":
        magnets = [obj]
    else:
        magnets = utils.get_magnets_for_site(session, api_server, headers, oid)

    if csvfile:
        # resolve before moving to the temporary directory
        csvfile = os.path.abspath(csvfile)

    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tempdir:
        try:
            os.chdir(tempdir)
            data_dir = os.path.join(tempdir, "data")
            os.makedirs(os.path.join(data_dir, "geometries"))
            os.makedirs(os.path.join(data_dir, "cad"))

            _fetch_geometries(session, api_server, headers, magnets, data_dir)

            env = appenv(
                envfile=None,
                url_api=data_dir,
                yaml_repo=os.path.join(data_dir, "geometries"),
                cad_repo=os.path.join(data_dir, "cad"),
                mesh_repo=data_dir,
                simage_repo=data_dir,
                mrecord_repo=data_dir,
                optim_repo=data_dir,
            )
            setup = msite_setup if mtype == "site" else magnet_setup
            Tubes, Helices, _OHelices, BMagnets, UMagnets, _Shims = setup(
                env, config_data["results"], debug
            )
            result = compute_inductance_matrix(
                Tubes, Helices, BMagnets, UMagnets, csvfile=csvfile, verbose=False
            )
        finally:
            os.chdir(cwd)

    _print_result(obj["name"], result)
    return result
