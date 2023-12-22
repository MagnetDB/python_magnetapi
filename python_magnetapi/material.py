"""
create material
"""

from . import utils


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
        print(f"material with name={data['name']} already exists")
        return None

    else:
        response = utils.post_json(
            session, api_server, headers, data, "material", verbose, debug
        )
        if response is None:
            print(f"material {data['name']} failed to be created")
            return None
        print(f"material {data['name']} created with id={response['id']}")
        return response["id"]
