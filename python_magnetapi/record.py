"""
create record
"""

import requests

from . import utils
from .exceptions import ResourceConflictError, ResourceNotFoundError
from .attachment import create as attach_create


def create(
    session: requests.Session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Create a record from a data dictionary.

    The referenced site must already exist.  The "file" field is uploaded as an
    attachment first; the resulting attachment ID is stored as "attachment_id".

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        data: record fields (must include "name", "site", and "file")
        verbose: enable verbose output
        debug: enable debug output

    Returns:
        ID of the newly created record.

    Raises:
        ResourceConflictError: if a record with the same name already exists.
        ResourceNotFoundError: if the referenced site name is not found.
    """

    _ids = utils.get_list(
        session, api_server, headers=headers, mtype="record"
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
        session, api_server, headers=headers, mtype="site"
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
        session, api_server, headers, data["file"]
    )
    del data["file"]
    print(f"data:{data}")

    # process record data: remove empty columns, rename columns, add Hoopstress data
    response = utils.post_json(
        session, api_server, headers, data, "clirecord"
    )
    print(f"record {data['name']} created with id={response['id']}")
    return response["id"]
