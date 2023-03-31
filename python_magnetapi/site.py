"""
create site
"""

import requests
from . import utils
from . import magnet


def create(
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
):
    """
    create a site from a data dictionnary
    """

    ids = utils.getlist(api_server, headers=headers, mtype="site", debug=debug)
    if data["name"] in ids:
        print(f"site with name={data['name']} already exists")
        return None

    else:
        # data: extract only necessary data for creation
        response = utils.postdata(api_server, headers, data, "site", verbose, debug)
        if response is None:
            print(f"site {data['name']} failed to be created")
            return None
        print(f"site {data['name']} created with id={response['id']}")

        # loop over magnets
        for magnet in data["magnets"]:
            _ids = utils.getlist(api_server, headers=headers, mtype="part", debug=debug)
            if magnet in _ids:
                _id = _ids[magnet]
                # how to create MagnetPart: use /api/magnets/{magnet_id}/parts
                # create(magnet_id: int, user=Depends(get_user('create')), part_id: int = Form(...))
            else:
                print(f"site {data['name']} failed to be created: no magnet {magnet}")

        # fill site_magnets see python_magnetdb/routes/api/site_magnets.py
        return response["id"]
