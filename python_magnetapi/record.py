"""
create record
"""

from . import utils
from .exceptions import ResourceConflictError, ResourceNotFoundError
from .attachment import create as attach_create


def create(
    session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
):
    """
    create a record from a data dictionnary
    """

    _ids = utils.get_list(
        session, api_server, headers=headers, mtype="record", debug=debug
    )
    if data["name"] in _ids:
        raise ResourceConflictError(
            f"Record '{data['name']}' already exists",
            object_name=data['name'],
            object_type='record',
            existing_id=_ids[data['name']]
        )

    # look for site
    _ids = utils.get_list(
        session, api_server, headers=headers, mtype="site", debug=debug
    )
    if data["site"] not in _ids:
        raise ResourceNotFoundError(
            f"Site '{data['site']}' not found. Create the site before creating record '{data['name']}'",
            object_name=data['site'],
            object_type='site',
            required_by=data['name']
        )
    
    _id = _ids[data["site"]]
    data["site_id"] = _id
    del data["site"]

    data["attachment_id"] = attach_create(
        session, api_server, headers, data["file"], verbose, debug
    )
    del data["file"]
    print(f"data:{data}")

    # process record data: remove empty columns, rename columns, add Hoopstress data
    response = utils.post_json(
        session, api_server, headers, data, "clirecord", verbose, debug=True
    )
    print(f"record {data['name']} created with id={response['id']}")
    return response["id"]
