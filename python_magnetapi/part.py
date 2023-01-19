"""
create part
"""

import requests
from . import utils
from . import material

def create(api_server: str, headers: dict, data: dict, verbose: bool=False, debug: bool=False):
    """
    create a part from a data dictionnary
    """

    ids = utils.getlist(api_server, headers=headers, mtype='part', debug=debug)
    if data['name'] in ids:
        print(f"part with name={data['name']} already exists")
        return None

    else:
        mdata = {}
        material.create(api_server, headers=headers, data=mdata, mtype='material', verbose=verbose, debug=debug)

        response = utils.postdata(api_server, headers, data, 'part', verbose, debug)
        if response is None:
            print(f"part {data['name']} failed to be created")
            return None
        print(f"part {data['name']} created with id={response['id']}")

        # add magnet info
        # add geometry: see add_geometry_to_part.py
        # add cad, ...
