"""
create site
"""

import requests
from . import utils
from . import magnet
from . import record


def create(
    session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
):
    """
    create a site from a data dictionnary
    """

    ids = utils.get_list(session, api_server, headers=headers, mtype="site", debug=debug)
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

        response = utils.post_data(session, api_server, headers, data, "site", verbose, debug)
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
                        session, api_server, headers, magnet, verbose=verbose, debug=debug
                    )

            else:
                raise RuntimeError(
                    f"site/create: unexpected type for magnet (type={type(magnet)}) - should be str or dict"
                )

            # call to api/sites/{site_id}/magnets with magnetid = _id
            if not _id is None:
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
