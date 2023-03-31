"""
create part
"""

import requests
from . import utils
from . import material


def create(
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
):
    """
    create a part from a data dictionnary
    """

    ids = utils.getlist(api_server, headers=headers, mtype="part", debug=debug)
    if data["name"] in ids:
        print(f"part with name={data['name']} already exists")
        return None

    else:
        # search or create material in db
        mat_name = data["material"]
        mat_ids = utils.getlist(
            api_server, headers=headers, mtype="material", debug=debug
        )
        if mat_name in ids:
            data["material_id"] = mat_ids[mat_name]
            del data["material"]
        else:
            print(f"part {data['name']} failed to be created: no material {mat_name}")
            return None

        # extract magnets list
        magnets = data["magnets"].copy()
        del data["magnets"]

        # get material id, and set data accordingly
        response = utils.postdata(api_server, headers, data, "part", verbose, debug)
        if response is None:
            print(f"part {data['name']} failed to be created")
            return None
        print(f"part {data['name']} created with id={response['id']}")

        # add magnets
        for magnet in magnets:
            _ids = utils.getlist(
                api_server, headers=headers, mtype="magnet", debug=debug
            )
            if magnet in _ids:
                _id = _ids[magnet]
                # how to create MagnetPart: use /api/magnets/{magnet_id}/parts
                # create(magnet_id: int, user=Depends(get_user('create')), part_id: int = Form(...))
            else:
                print(
                    f"part {data['name']} failed to be created MagnetPart: no magnet {magnet}"
                )

        # add magnet info
        # add geometry: see add_geometry_to_part.py
        # add cad, ...
        # see also status in python_magnetdb/models/status.py
        # how to change timestamps

        return response["id"]
