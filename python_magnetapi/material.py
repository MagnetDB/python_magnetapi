"""
create material
"""

import requests

from . import utils
from .exceptions import ResourceConflictError


def create(
    session: requests.Session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Create a material from a data dictionary.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        data: material fields (must include "name")
        verbose: enable verbose output
        debug: enable debug output

    Returns:
        ID of the newly created material.

    Raises:
        ResourceConflictError: if a material with the same name already exists.
    """

    ids = utils.get_list(
        session, api_server, headers=headers, mtype="material"
    )
    if data["name"] in ids:
        raise ResourceConflictError(
            f"Material '{data['name']}' already exists",
            object_name=data["name"],
            object_type="material",
            existing_id=ids[data["name"]],
        )

    response = utils.post_json(
        session, api_server, headers, data, "material"
    )
    print(f"material {data['name']} created with id={response['id']}")
    return response["id"]
