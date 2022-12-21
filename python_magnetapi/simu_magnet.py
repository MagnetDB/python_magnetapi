import os
import sys
import datetime
from datetime import timezone
from datetime import datetime
from time import sleep

import requests

api_server = os.getenv('MAGNETDB_API_SERVER') or "http://magnetdb-api.grenoble.lncmi.local"
magnet_name = 'HL-test'
server_name = 'calcul22'

r = requests.get(
    f"{api_server}:8000/api/magnets",
    headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
)

def get_simulation(id: int):
    return requests.get(
        f"{api_server}:8000/api/simulations/{id}",
        headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
    ).json()

result_list = r.json()['items']
for magnet in result_list:
    print(f"MAGNET: {magnet['name']} (status:{magnet['status']}, id:{magnet['id']})")
    if magnet['name'] == magnet_name:
        found = True
        break

if not found:
    print(f"magnet: {magnet_name} not found in magnetdb ({api_server})")
    print(f"available magnets: {[magnet['name'] for magnet in result_list]}")
    sys.exit(1)

# Create a simu

sim_data={
    'resource_type': 'magnet',
    'resource_id': magnet['id'],
    'method': 'cfpdes',
    'model': 'thmagel_hcurl',
    'geometry': 'Axi',
    'cooling': 'meanH',
    'static': True,
    'non_linear': False
    }
   
print(sim_data)

ct = datetime.utcnow()
print(f"current time: {datetime.now()}")
print(f"current time (UTC): {datetime.utcnow()}")
# print(f"current time: {ct.replace(tzinfo=timezone.utc)}")

requests.post(
    f"{api_server}:8000/api/simulations",
    data=sim_data,
    headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
)

# how to get simu_id
r = requests.get(f"{api_server}:8000/api/simulations", headers={'Authorization': os.getenv('MAGNETDB_API_KEY')})
print(f"result: type={type(r.json()['items'])}")
result_list = r.json()['items']
simu = result_list[-1]
simu_id = simu['id']

# however shall check timestamp and author
print(f"simu_id={simu['id']}: create_at={simu['created_at']}, ct={ct}")
t1 = datetime.strptime(simu['created_at'], "%Y-%m-%dT%X.%f")
print(f"t1: {t1}")
diff = t1 - ct
print(f'tdiff: {diff} seconds: {diff.seconds}  milliseconds: {diff.microseconds/1000.}')    

# # how to get user name?
# from db result_list[-1]['owner']['name']:
    
# Run setup
print("Setup simulation...")
r = requests.post(
    f"{api_server}:8000/api/simulations/{simu_id}/run_setup",
    headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
)
while True:
    simulation = get_simulation(simu_id)
    if simulation['setup_status'] in ['failed', 'done']:
        break
    sleep(1)

print(f"Setup done: status={simulation['setup_status']}")
if simulation['setup_status'] == 'failed':
    sys.exit(1)

# Get server id
r = requests.get(f"{api_server}:8000/api/servers", headers={'Authorization': os.getenv('MAGNETDB_API_KEY')})
print(f"result: type={type(r.json()['items'])}")
result_list = r.json()['items']
for server in result_list:
    print(f"server: {server['name']}, id:{server['id']})")
    if server['name'] == server_name:
        found = True
        break

if not found:
    print(f"server: {server['name']} not found")
    print(f"available servers: {[server['name'] for server in result_list]}")
    sys.exit(1)
print(f'server: {server}')

print("Starting simulation...")
r = requests.post(
    f"{api_server}:8000/api/simulations/{simu_id}/run",
    data={'server_id': 4},
    headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
)
while True:
    simulation = get_simulation(simu_id)
    if simulation['status'] in ['failed', 'done']:
        break
    sleep(10)
print(f"Simulation done: status={simulation['status']}")

if simulation['status'] == 'failed':
    sys.exit(1)

r = requests.get(f"{api_server}:8000/api/attachments/{simulation['log_attachment_id']}/download",
                 headers={'Authorization': os.getenv('MAGNETDB_API_KEY')})
print(r.text)
