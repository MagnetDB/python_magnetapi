"""
create site
"""

import requests
from . import utils

def create(api_server: str, headers: dict, data: dict, verbose: bool=False, debug: bool=False):
    """
    create a site from a data dictionnary
    """

    ids = utils.getlist(api_server, headers=headers, mtype='site', debug=debug)
    if data['name'] in ids:
        print(f"site with name={data['name']} already exists")
        return None

    else:
        # data: extract only necessary data for creation
        r = requests.post(
            f"{api_server}/api/sites",
            data=data,
            headers=headers
        )

        response = r.json()
        if r.status_code != 200:
            print(response['detail'])

        print(f"site {data['name']} created with id={response['id']}")

        # loop over magnets
        # look for magnets
        _ids = utils.getlist(api_server, headers=headers, mtype='magnet', debug=debug)
        if not data['material'] in ids:
            print(f"create(site, name={data['name']}): magnet with name={data['material']} does not exist - must be created first")
            return None
        else:
            _id = _ids[data['material']]
            data['magnet_id'] = _id
            # drop data['material']
            data.drop('material')

        # /api/sites/{site_id}/magnets + params=magnet_id
 
