import os
import sys
import json
import requests

api_server = os.getenv("MAGNETDB_API_SERVER") or "http://magnetdb-api.lncmig.local"

material_name = "mtore"
r = requests.get(
    f"{api_server}:8000/api/materials",
    headers={"Authorization": os.getenv("MAGNETDB_API_KEY")},
)

material_id = -1
result_list = r.json()["items"]
for material in result_list:
    # print(f"MATERIAL: {material['name']} ( id:{material['id']})")
    if material["name"] == material_name:
        material_id = material["id"]
        break


if material_id == -1:
    print(f"materials: {material_name} not found in magnetdb ({api_server})")
    available = [material["name"] for material in result_list]
    print(f"available materials ({len(available)}): {available}")
    sys.exit(1)

data = {
    "name": "testHelix15",
    "description": "helix from cli",
    "type": "helix",
    "material_id": material_id,
    "desing_office_reference": "xyezgv",
}
print(json.dumps(data))
r = requests.post(
    f"{api_server}:8000/api/parts",
    data=data,
    headers={"Authorization": os.getenv("MAGNETDB_API_KEY")},
)

data = r.json()
if r.status_code != 200:
    print(f"failed to create part: {data['detail']}")
else:
    print(f"PART: {data['name']} (material:{data['material']}, id:{data['id']})")

# r = requests.get(f"{api_server}/api/parts/{{data['id']})}", headers={'Authorization': os.getenv('MAGNETDB_API_KEY')})
# data = r.json()

file = "/data/geometries/HL-31_H1.yaml"

updated_data = {
    "name": data["name"],
    "description": "updated helix from cli",
    "type": "helix",
    "material_id": data["material_id"],
    "desing_office_reference": "ZERTYU",
}
print(f"updated_data={updated_data}")
r = requests.patch(
    f"{api_server}:8000/api/parts/{data['id']}",
    data=updated_data,
    headers={"Authorization": os.getenv("MAGNETDB_API_KEY")},
)

data = r.json()
print(f"patch: {data}")
if r.status_code != 200:
    print(f"failed to update part: {data}")
