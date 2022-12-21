import os
import re

import requests

api_server = os.getenv('MAGNETDB_API_SERVER') or "http://magnetdb-api.grenoble.lncmi.local:8000"

with open('README.md') as file:
    r = requests.get(f"{api_server}/api/magnets/1", headers={'Authorization': os.getenv('MAGNETDB_API_KEY')})
    magnet = r.json()

    r = requests.patch(
        f"{api_server}/api/magnets/1",
        data={
            'name': magnet['name'],
            'design_office_reference': magnet['design_office_reference'],
            'description': 'Geometry updated by API.'
        },
        files={'geometry': file},
        headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
    )
    print(r.json())
