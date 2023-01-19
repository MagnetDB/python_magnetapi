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
        response = utils.postdata(api_server, headers, data, 'material', verbose, debug)
        if response is None:
            print(f"material {data['name']} failed to be created")
            return None
        print(f"material {data['name']} created with id={response['id']}")
