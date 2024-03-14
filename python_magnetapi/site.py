"""
create site
"""

from . import utils
from datetime import datetime

# from . import magnet
# from . import record


def create(
    session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """
    create a site from a data dictionnary
    """

    ids = utils.get_list(
        session, api_server, headers=headers, mtype="site", debug=debug
    )
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

        records = []
        if "records" in data:
            records = data["records"].copy()
            del data["records"]

        if "status" in data:
            del data["status"]

        response = utils.post_data(
            session, api_server, headers, data, "site", verbose, debug
        )
        if response is None:
            print(f"site {data['name']} failed to be created")
            return None
        print(f"site {data['name']} created with id={response['id']}")

        # loop over magnets
        site_id = response["id"]

        for magnet in magnets:
            _ids = utils.get_list(
                session, api_server, headers=headers, mtype="magnet", debug=debug
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
                        verbose=verbose,
                        debug=debug,
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
                        verbose=verbose,
                        debug=debug,
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
                    verbose=verbose,
                    debug=debug,
                )

        for record in records:
            if not isinstance(record, dict):
                raise RuntimeError(
                    f"site/create: unexpected type for record (type={type(record)}) - should be dict"
                )
            _id = record.create(
                session, api_server, headers, record, verbose=verbose, debug=debug
            )

        # update site description
        # update status
        # putinoperation: patch /api/sites/{id}/put_in_operation
        # shutdown: patch "/api/sites/{id}/shutdown
        return response["id"]


def status(
    session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
) -> bool:
    """
    set site status

    /api/sites/{id}/put_in_operation
    /api/sites/{id}/shutdown

    from magnetdb.models.status.py:
    class Status:

    data:
    name: of site
    id:
    status:
    date:

    see python_magnetdb.models.status.py:
    IN_STUDY = "in_study"
    IN_STOCK = "in_stock"
    IN_OPERATION = "in_operation"
    DEFUNCT = "defunct"
    """
    print(f"site.status: data={data}", flush=True)

    if "id" not in data:
        if "name" not in data:
            raise RuntimeError(
                f"site/status: invalid data={data} - missing id or name key"
            )

        ids = utils.get_list(
            session, api_server, headers=headers, mtype="site", debug=debug
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
                debug=debug,
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
