"""
create magnet
"""

import requests

from . import utils
from .exceptions import ResourceConflictError

# from . import part
# from . import site


def create(
    session: requests.Session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
) -> int | None:
    """Create a magnet from a data dictionary.

    Parts and sites listed in *data* are linked after the magnet is created.
    Geometry files, if provided, are uploaded to the geometry endpoint.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        data: magnet fields (must include "name"); may contain "parts", "sites",
              and "geometry" lists which are processed separately
        verbose: enable verbose output
        debug: enable debug output

    Returns:
        ID of the newly created magnet, or None if creation failed.

    Raises:
        ResourceConflictError: if a magnet with the same name already exists.
        RuntimeError: if a part or site entry has an unexpected type.
    """

    ids = utils.get_list(
        session, api_server, headers=headers, mtype="magnet"
    )
    if data["name"] in ids:
        raise ResourceConflictError(
            f"Magnet '{data['name']}' already exists",
            object_name=data['name'],
            object_type='magnet',
            existing_id=ids[data['name']]
        )

    parts = []
    if "parts" in data:
        parts = data["parts"].copy()
        del data["parts"]

    sites = []
    if "sites" in data:
        sites = data["sites"].copy()
        del data["sites"]

    geometries = []
    if "geometry" in data:
        geometries = data["geometry"].copy()
        del data["geometry"]

    status = ""
    if "status" in data:
        status = data["status"]
        del data["status"]

    # data: extract only necessary data for creation
    print(f"create:magnet data={data}")
    response = utils.post_data(
        session, api_server, headers, data, "magnet"
    )
    print(f"create:magnet response={response}")
    if response is None:
        print(f"create:magnet {data['name']} failed to be created")
        return None
    else:
        print(f"create:magnet {data['name']} created with id={response['id']}")

    # loop over parts
    magnet_id = response["id"]
    for part in parts:
        _ids = utils.get_list(
            session, api_server, headers=headers, mtype="part"
        )
        if isinstance(part, str):
            # TODO if part is a string use procedure bellow,
            # otherwise if part is a dict simple call create method from part.py
            if part in _ids:
                pdata = {"part_id": _ids[part]}
                # how to create MagnetPart: use /api/magnets/{magnet_id}/parts
                # create(magnet_id: int, user=Depends(get_user('create')), part_id: int = Form(...))
                print(
                    f"create:magnet  {data['name']} attach part id={pdata['part_id']} name={part}"
                )
                utils.add_data_to_object(
                    session,
                    api_server,
                    headers,
                    magnet_id,
                    data=pdata,
                    mtype="magnet",
                    dtype="part",
                )
            else:
                print(
                    f"create:magnet {data['name']} failed to add part {part} - no such part"
                )

        elif isinstance(part, dict):
            pname = part["name"]
            _id = -1
            if pname in _ids:
                _id = pdata = {"part_id": _ids[part]}
            else:
                _id = part.create(
                    api_server, headers, part
                )

            print(
                f"create:magnet {data['name']}  attach part id={_id} name={pname}"
            )
            utils.add_data_to_object(
                session,
                api_server,
                headers,
                magnet_id,
                data={"part_id": _id},
                mtype="magnet",
                dtype="part",
            )
        else:
            raise RuntimeError(
                f"create:magnet  {data['name']} unexpected type for part (type={type(part)}) - should be str or dict"
            )

    for site in sites:
        _ids = utils.get_list(
            session, api_server, headers=headers, mtype="site"
        )
        if isinstance(site, str):
            if site in _ids:
                site_id = _ids[site]

                print(
                    f"create:magnet {data['name']}  attach site id={_id} name={site}"
                )
                utils.add_data_to_object(
                    session,
                    api_server,
                    headers,
                    site_id,
                    data={"magnet_id": magnet_id},
                    mtype="site",
                    dtype="magnet",
                )

            else:
                print(
                    f"create:magnet {data['name']} failed to attach to site {site} - no such site"
                )

        else:
            raise RuntimeError(
                f"magnet {data['name']} failed to attach to site {site} - unexpected type ({type(site)}"
            )

    # add magnet geometry
    if geometries:
        geomfile = f"{geometries[0]}.yaml"
        utils.add_data_files_to_object(
            session,
            api_server,
            headers,
            response["id"],
            "magnet",
            "geometrie",
            data={"type": "default"},
            files={"geometry": geomfile},
        )

    # add cad
    # add status

    return response["id"]
