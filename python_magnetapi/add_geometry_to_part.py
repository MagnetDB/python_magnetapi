import os

import requests

api_server = os.getenv('MAGNETDB_API_SERVER') or "http://magnetdb-api.grenoble.lncmi.local:8000"

with open('README.md') as file:
    r = requests.post(
        f"{api_server}/api/parts/1/geometries",
        data={'type': 'default'},
        files={'geometry': file},
        headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
    )
    print(r.json())
