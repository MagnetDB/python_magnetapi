"""
create magnet
"""

import requests
from . import utils
from .part import create as part_create


def create(
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
):
    """
    create a magnet from a data dictionnary
    """

    ids = utils.getlist(api_server, headers=headers, mtype="magnet", debug=debug)
    if data["name"] in ids:
        print(f"magnet with name={data['name']} already exists")
        return None

    else:
        # data: extract only necessary data for creation
        response = utils.postdata(api_server, headers, data, "magnet", verbose, debug)
        if response is None:
            print(f"magnet {data['name']} failed to be created")
            return None
        else:
            print(f"magnet {data['name']} created with id={response['id']}")

        # loop over parts
        for part in data["parts"]:
            _ids = utils.getlist(api_server, headers=headers, mtype="part", debug=debug)
            if part in _ids:
                _id = _ids[part]
                # how to create MagnetPart: use /api/magnets/{magnet_id}/parts
                # create(magnet_id: int, user=Depends(get_user('create')), part_id: int = Form(...))
            else:
                print(
                    f"magnet {data['name']} failed to be created MagnetPart: no part {part}"
                )

        for site in data["sites"]:
            _ids = utils.getlist(api_server, headers=headers, mtype="site", debug=debug)
            if site in _ids:
                _id = _ids[site]
                # how to create MagnetPart: use /api/magnets/{magnet_id}/parts
                # create(magnet_id: int, user=Depends(get_user('create')), part_id: int = Form(...))
            else:
                print(
                    f"magnet {data['name']} failed to be created SiteMagnet: no site {site}"
                )

        # fill magnet_parts see python_magnetdb/routes/api/magnet_parts.py
        # add geometry data: see add_geometry_to_magnet.py
        # add cad
        # add status

        return response["id"]
