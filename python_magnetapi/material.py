"""
create material
"""

import requests
from . import utils

def create(api_server: str, headers: dict, data: dict, verbose: bool=False, debug: bool=False):
    """
    create a material from a data dictionnary
    """

    ids = utils.getlist(api_server, headers=headers, mtype='material', debug=debug)
    if data['name'] in ids:
        print(f"material with name={data['name']} already exists")
        return None

    else:
        r = requests.post(
            f"{api_server}/api/materials",
            data=data,
            headers=headers
        )

        response = r.json()
        if r.status_code != 200:
            print(response['detail'])

        print(f"material {data['name']} created with id={response['id']}")
