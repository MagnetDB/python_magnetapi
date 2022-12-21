import os

import requests

api_server = os.getenv('MAGNETDB_API_SERVER') or "http://magnetdb-api.grenoble.lncmi.local"

material = 'tutu'
r = requests.get(
    f"{api_server}:8000/api/materials",
    headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
)

result_list = r.json()['items']
for material in result_list:
    print(f"MATERIAL: {material['name']} ( id:{material['id']})")
    if material['name'] == material_name:
        found = True
        break


if not found:
    print(f"materials: {material_name} not found in magnetdb ({api_server})")
    print(f"available materials: {[part['name'] for material in result_list]}")
    sys.exit(1)

# part = Part(name=name, description=description, status='in_study', type=type,
    #             design_office_reference=design_office_reference)
    # part.material().associate(material)

r = requests.post(
    f"{api_server}:8000/api/parts",
    data={'name': input('Part name? '),
          'description' : ,
          'type':,
          'material_id' ,
          'desing_office_reference'
          }
    headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
)

data = r.json()
if r.status_code != 200:
    print(data['detail'])
else:
    print(f"PART: {data['name']} (material:{data['material']}, id:{data['id']})")

# r = requests.get(f"{api_server}/api/parts/{{data['id']})}", headers={'Authorization': os.getenv('MAGNETDB_API_KEY')})
# data = r.json()

r = requests.patch(
    f"{api_server}/api/magnets/{{data['id']})}",
    data={
        'name': data['name'],
        'description': 'Part updated by API.'
          'type':,
          'material_id' ,
          'desing_office_reference'
    },
    files={'geometry': file},
    headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
)
print(r.json())
