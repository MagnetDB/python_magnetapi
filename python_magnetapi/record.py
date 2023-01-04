"""
create record
"""

import requests
from . import utils

def create(api_server: str, headers: dict, data: dict, verbose: bool=False, debug: bool=False):
    """
    create a record from a data dictionnary
    """

    ids = utils.getlist(api_server, headers=headers, mtype='record', debug=debug)
    if data['name'] in ids:
        print(f"record with name={data['name']} already exists")
        return None

    else:
        # look for site
        _ids = utils.getlist(api_server, headers=headers, mtype='site', debug=debug)
        if not data['site'] in ids:
            print(f"create(record, name={data['name']}): site with name={data['material']} does not exist - must be created first")
            return None
        else:
            _id = _ids[data['site']]
            data['site_id'] = _id
            # drop data['material']
            data.drop('site')

        r = requests.post(
            f"{api_server}/api/records",
            data=data,
            headers=headers
        )

        response = r.json()
        if r.status_code != 200:
            print(response['detail'])

        print(f"record {data['name']} created with id={response['id']}")
