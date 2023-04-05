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

    ids = utils.get_list(api_server, headers=headers, mtype="site", debug=debug)
    if data["name"] in ids:
        print(f"site with name={data['name']} already exists")
        return None

    else:
        # data: extract only necessary data for creation
        magnets = []
        if "magnets" in data:
            magnets = data["magnets"].copy()
            del data["magnets"]

        if "status" in data:
            del data["status"]

        response = utils.post_data(api_server, headers, data, "site", verbose, debug)
        if response is None:
            print(f"site {data['name']} failed to be created")
            return None
        print(f"site {data['name']} created with id={response['id']}")

        # loop over magnets
        site_id = response["id"]

        for magnet in data["magnets"]:
            _ids = utils.getl_ist(
                api_server, headers=headers, mtype="part", debug=debug
            )
            if magnet in _ids:
                _id = _ids[magnet]
                # how to create MagnetPart: use /api/magnets/{magnet_id}/parts
                # create(magnet_id: int, user=Depends(get_user('create')), part_id: int = Form(...))
                utils.add_data_to_object(
                    api_server,
                    headers,
                    site_id,
                    mtype="site",
                    dtype="magnet",
                    data={"magnet_id": _id},
                    verbose=verbose,
                    debug=debug,
                )
            else:
                print(
                    f"site {data['name']} failed to add magnet {magnet} - no such magnet"
                )

        # add site description
        return response["id"]
