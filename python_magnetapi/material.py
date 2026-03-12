"""
create material
"""

from . import utils
from .exceptions import ResourceConflictError


def create(
    session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
):
    """
    create a material from a data dictionnary
    """

    ids = utils.get_list(
        session, api_server, headers=headers, mtype="material", debug=debug
    )
    if data["name"] in ids:
        raise ResourceConflictError(
            f"Material '{data['name']}' already exists",
            object_name=data["name"],
            object_type="material",
            existing_id=ids[data["name"]],
        )

    response = utils.post_json(
        session, api_server, headers, data, "material", verbose, debug
    )
    print(f"material {data['name']} created with id={response['id']}")
    return response["id"]
