"""
create magnet
"""

import requests
from . import utils

def create(api_server: str, headers: dict, data: dict, verbose: bool=False, debug: bool=False):
    """
    create a magnet from a data dictionnary
    """

    ids = utils.getlist(api_server, headers=headers, mtype='magnet', debug=debug)
    if data['name'] in ids:
        print(f"magnet with name={data['name']} already exists")
        return None

    else:
        # look for parts
        part_ids = utils.getlist(api_server, headers=headers, mtype='part', debug=debug)
        if not data['material'] in ids:
            print(f"create(magnet, name={data['name']}): part with name={data['material']} does not exist - must be created first")
            return None
        else:
            _id = part_ids[data['material']]
            data['material_id'] = _id
            # drop data['material']
            data.drop('material')

        # add created_at to data
        # eventually add cao_attachment_id: aka xao and brep
        # eventually add geometry_attachment_id: aka yaml cfgfile, cut file, shape file,...
 
        r = requests.post(
            f"{api_server}/api/magnets",
            data=data,
            headers=headers
        )

        response = r.json()
        if r.status_code != 200:
            print(response['detail'])

        print(f"magnet {data['name']} created with id={response['id']}")
