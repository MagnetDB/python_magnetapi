"""
create site
"""

import requests

from . import utils
from .exceptions import ResourceConflictError
from datetime import datetime

# from . import magnet
# from . import record


def create(
    session: requests.Session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
) -> int | None:
    """Create a site from a data dictionary.

    Magnets and records listed in *data* are linked after the site is created.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        data: site fields (must include "name"); may contain "magnets" and
              "records" lists which are processed separately
        verbose: enable verbose output
        debug: enable debug output

    Returns:
        ID of the newly created site, or None if creation failed.

    Raises:
        ResourceConflictError: if a site with the same name already exists.
        RuntimeError: if a magnet or record entry has an unexpected type.
    """

    ids = utils.get_list(
        session, api_server, headers=headers, mtype="site"
    )
    if data["name"] in ids:
        raise ResourceConflictError(
            f"Site '{data['name']}' already exists",
            object_name=data["name"],
            object_type="site",
            existing_id=ids[data["name"]],
        )

    # data: extract only necessary data for creation
    magnets = []
    if "magnets" in data:
        magnets = data["magnets"].copy()
        del data["magnets"]

    if "status" in data:
        del data["status"]

    records = []
    if "records" in data:
        records = data["records"].copy()
        del data["records"]

    if "status" in data:
        del data["status"]

    response = utils.post_data(
        session, api_server, headers, data, "site"
    )
    if response is None:
        print(f"site {data['name']} failed to be created")
        return None
    print(f"site {data['name']} created with id={response['id']}")

    # loop over magnets
    site_id = response["id"]

    for magnet in magnets:
        _ids = utils.get_list(
            session, api_server, headers=headers, mtype="magnet"
        )

        _id = None
        mname = None
        if isinstance(magnet, str):
            mname = magnet
            if magnet in _ids:
                _id = _ids[magnet]
                utils.add_data_to_object(
                    session,
                    api_server,
                    headers,
                    site_id,
                    mtype="site",
                    dtype="magnet",
                    data={"magnet_id": _id},
                )
            else:
                print(
                    f"site {data['name']} failed to add magnet {magnet} - no such magnet"
                )

        elif isinstance(magnet, dict):
            mname = magnet["name"]
            _id = -1
            if mname in _ids:
                _id = _ids[magnet["name"]]
            else:
                _id = magnet.create(
                    session,
                    api_server,
                    headers,
                    magnet,
                )

        else:
            raise RuntimeError(
                f"site/create: unexpected type for magnet (type={type(magnet)}) - should be str or dict"
            )

        # call to api/sites/{site_id}/magnets with magnetid = _id
        if _id is not None:
            print(f"create:site attach magnet id={_id} name={mname}")
            utils.add_data_to_object(
                session,
                api_server,
                headers,
                site_id,
                mtype="site",
                dtype="magnet",
                data={"magnet_id": _id},
            )

    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError(
                f"site/create: unexpected type for record (type={type(record)}) - should be dict"
            )
        _id = record.create(
            session, api_server, headers, record
        )

    # update site description
    # update status
    # putinoperation: patch /api/sites/{id}/put_in_operation
    # shutdown: patch "/api/sites/{id}/shutdown
    return response["id"]


def status(
    session: requests.Session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
) -> bool:
    """Set the operational status of a site.

    Calls PUT /api/sites/{id}/put_in_operation or /api/sites/{id}/shutdown
    depending on the requested status.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        data: dict with keys:
            - "name" or "id": site identifier
            - "status": one of "in_study", "in_stock", "in_operation"
            - "date": timestamp string in "%Y.%m.%d %H:%M:%S" format
        verbose: enable verbose output
        debug: enable debug output

    Returns:
        True on success, False if the site is not found or the request failed.

    Raises:
        RuntimeError: if "name"/"id" is missing or status value is unknown.
    """
    print(f"site.status: data={data}", flush=True)

    if "id" not in data:
        if "name" not in data:
            raise RuntimeError(
                f"site/status: invalid data={data} - missing id or name key"
            )

        ids = utils.get_list(
            session, api_server, headers=headers, mtype="site"
        )
        if data["name"] not in ids:
            print(f"site with name={data['name']} does not exist")
            return False
        data["id"] = ids[data["name"]]
    else:
        if "name" not in data:
            sdata = utils.get_object(
                session,
                api_server,
                headers=headers,
                mtype="site",
                id=data["id"],
            )
            data["name"] = sdata["name"]

    # do we need to convert to timestamp
    # post: data = {'[de]commissioned_at': }
    print(f'date={data["date"]}, type={type(data["date"])}', flush=True)
    print(
        f'site: id={data["id"]}, status={data["status"]}, date={data["date"]}',
        flush=True,
    )

    tformat = "%Y.%m.%d %H:%M:%S"
    match data["status"]:
        case "in_study":
            return True
        case "in_stock":
            # /api/sites/{id}/shutdown
            tdata = {"decommissioned_at": datetime.strptime(data["date"], tformat)}
            print(f"tdata={tdata}")
            response = session.post(
                f"{api_server}/api/sites/{data['id']}/shutdown",
                data=tdata,
                headers=headers,
            )
        case "in_operation":
            # /api/sites/{id}/put_in_operation
            tdata = {"commissioned_at": datetime.strptime(data["date"], tformat)}
            print(f"tdata={tdata}")
            response = session.post(
                f"{api_server}/api/sites/{data['id']}/put_in_operation",
                data=tdata,
                headers=headers,
            )
        case _:
            raise RuntimeError(f'site/status: status={data["status"]} unknown')

    if response is None:
        print(
            f"site:status: id={data['id']}, name={data['name']}, failed to set status {data['status']}"
        )
        return False

    print(f"site/status: response={response}", flush=True)
    print(response.status_code)
    print(response.reason)
    print(response.json())

    return True
