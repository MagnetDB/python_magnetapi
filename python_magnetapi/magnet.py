"""
create magnet
"""

import requests
from . import utils
from . import part

def create(api_server: str, headers: dict, data: dict, verbose: bool=False, debug: bool=False):
    """
    create a magnet from a data dictionnary
    """

    ids = utils.getlist(api_server, headers=headers, mtype='magnet', debug=debug)
    if data['name'] in ids:
        print(f"magnet with name={data['name']} already exists")
        return None

    else:
        # data: extract only necessary data for creation
        response = utils.postdata(api_server, headers, data, 'magnet', verbose, debug)
        if response is None:
            print(f"magnet {data['name']} failed to be created")
            return None
        else:
            print(f"magnet {data['name']} created with id={response['id']}")

            # loop over magnets
            for part in data['parts']:
                pdata = {}
                part.create(api_server, headers=headers, data=pdata, mtype='part', verbose=verbose, debug=debug)

        # fill magnet_parts see python_magnetdb/routes/api/magnet_parts.py
        # add geometry data: see add_geometry_to_magnet.py
        # add cad
