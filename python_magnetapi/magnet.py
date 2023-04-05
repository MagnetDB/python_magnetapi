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

    ids = utils.get_list(api_server, headers=headers, mtype="magnet", debug=debug)
    if data["name"] in ids:
        print(f"magnet with name={data['name']} already exists")
        return None

    else:
        parts = []
        if "parts" in data:
            parts = data["parts"].copy()
            del data["parts"]

        sites = []
        if "sites" in data:
            sites = data["sites"].copy()
            del data["sites"]

        if "status" in data:
            del data["status"]

        # data: extract only necessary data for creation
        response = utils.post_data(api_server, headers, data, "magnet", verbose, debug)
        if response is None:
            print(f"magnet {data['name']} failed to be created")
            return None
        else:
            print(f"magnet {data['name']} created with id={response['id']}")

        # loop over parts
        magnet_id = response["id"]
        for part in parts:
            _ids = utils.get_list(
                api_server, headers=headers, mtype="part", debug=debug
            )
            # TODO if part is a string use procedure bellow,
            # otherwise if part is a dict simple call create method from part.py
            if part in _ids:
                pdata = {"part_id": _ids[part]}
                # how to create MagnetPart: use /api/magnets/{magnet_id}/parts
                # create(magnet_id: int, user=Depends(get_user('create')), part_id: int = Form(...))
                utils.add_data_to_object(
                    api_server,
                    headers,
                    magnet_id,
                    mtype="magnet",
                    dtype="part",
                    data=pdata,
                    verbose=verbose,
                    debug=debug,
                )
            else:
                print(f"magnet {data['name']} failed to add part {part} - no such part")

        for site in sites:
            _ids = utils.get_list(
                api_server, headers=headers, mtype="site", debug=debug
            )
            if site in _ids:
                site_id = _ids[site]
                # how to create MagnetPart: use /api/magnets/{magnet_id}/parts
                # create(magnet_id: int, user=Depends(get_user('create')), part_id: int = Form(...))
                utils.add_data_to_object(
                    api_server,
                    headers,
                    site_id,
                    mtype="site",
                    dtype="magnet",
                    data={"magnet_id": magnet_id},
                    verbose=verbose,
                    debug=debug,
                )
            else:
                print(
                    f"magnet {data['name']} failed to attach to site {site} - no such site"
                )

        # add magnet info
        # add cad
        # add status

        return response["id"]
