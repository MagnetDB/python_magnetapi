import os

import requests

api_server = os.getenv('MAGNETDB_API_SERVER') or "http://magnetdb-api.grenoble.lncmi.local"

r = requests.post(
    f"{api_server}:8000/api/magnets",
    data={'name': input('Magnet name? ')},
    headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
)

data = r.json()
if r.status_code != 200:
    print(data['detail'])
else:
    print(f"MAGNET: {data['name']} (status:{data['status']}, id:{data['id']})")
