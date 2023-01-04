"""
create part
"""

import requests
from . import utils

def create(api_server: str, headers: dict, data: dict, verbose: bool=False, debug: bool=False):
    """
    create a part from a data dictionnary
    """

    ids = utils.getlist(api_server, headers=headers, mtype='part', debug=debug)
    if data['name'] in ids:
        print(f"part with name={data['name']} already exists")
        return None

    else:
        # look for material
        material_ids = utils.getlist(api_server, headers=headers, mtype='material', debug=debug)
        if not data['material'] in ids:
            print(f"create({mtype}, name={data['name']}): material with name={data['material']} does not exist - must be created first")
            return None
        else:


        r = requests.post(
            f"{api_server}/api/parts",
            data=data,
            headers=headers
        )

        response = r.json()
        if r.status_code != 200:
            print(response['detail'])

        print(f"part {data['name']} created with id={response['id']}")
