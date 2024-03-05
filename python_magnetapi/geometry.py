"""
create geometry
"""

import os
from . import utils
import json
import requests


valid_geometry_types = {
    "Helix": ["salome", "catia", "cam", "shape"],
    "Supra": ["hts"],
}


def create(
    session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
):
    """
    create a geometry from a data dictionnary

    data: dict with following entries
    name: file
    part_name:
    type: (see web/src/views/parts/show/GeometryEditor.vue
        helix: default (.yaml), salome (cut.dat), catia (xls), cam (iso), shape (dat),
        supra: hts
        others: default


    """
    pwd = os.getcwd()
    print(f"geometry/create: data={data}, cwd={pwd}", flush=True)
    file = data["name"]
    # check if file exists
    if not os.path.isfile(file):
        raise RuntimeError(f"geometry/create: {file} does not exist")
    (basedir, basename) = os.path.split(file)
    print(f"geometry/create: basedir={basedir}, basename={basename}", flush=True)
    if basedir:
        os.chdir(basedir)

    # attachment will be created (to be changed)
    files = {"attachment": open(basename, "rb")}
    # files["data"] = json.dumps(data)

    # recover part_id
    ids = utils.get_list(
        session, api_server, headers=headers, mtype="part", debug=debug
    )
    if data["part_name"] in ids:
        part_id = ids[data["part_name"]]
    else:
        print(
            f"part with name={data['part_name']} not found in existing parts ({list(ids.keys())}"
        )
        return None

    # check type if consistant with part type
    if data["type"] != "default":
        part_data = utils.get_object(
            session,
            api_server,
            headers=headers,
            mtype="part",
            id=part_id,
            debug=debug,
        )
        print(f"shall check type={data['type']} if consistant with {part_data['type']}")

    print(f"create/geometry: files={files}", flush=True)

    # create an attachment
    try:
        """
        use add_data_files_to_object from utils
        """
        response = session.post(
            f"{api_server}/api/parts/{part_id}/geometries",
            files=files,
            data=data,
            headers=headers,
        )
    except FileNotFoundError:
        print(f"{file} was not found.")
    except requests.exceptions.RequestException as e:
        print(f"There was an exception that occurred while handling your request {e}.")

    if response is None:
        print(f"{file}: failed to create geometry {data}")
        return None

    os.chdir(pwd)
    print(f"geometry/create: response={response}", flush=True)
    print(response.status_code)
    print(response.reason)
    print(response.json())

    # Get part data
    part_data = utils.get_object(
        session,
        api_server,
        headers=headers,
        mtype="part",
        id=part_id,
        debug=debug,
    )
    geom_id = part_data["geometries"][0]["id"]
    geom_attached_id = part_data["geometries"][0]["attachment"]["id"]
    geom_attached_name = part_data["geometries"][0]["attachment"]["filename"]
    print(
        f"geometry/create: geom_id={geom_id}, geom_attached_id={geom_attached_id}, geom_attached_name={geom_attached_name}"
    )
    return geom_id
