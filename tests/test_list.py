import os
import pytest
import json
import requests

# add  @pytest.fixture to declare context

api_server = os.getenv("MAGNETDB_API_SERVER") or "api.magnetdb-dev.local"
api_key = os.getenv("MAGNETDB_API_KEY")

headers = {"Authorization": os.getenv("MAGNETDB_API_KEY")}
web = f"https://{api_server}"
# port = 8000
# web = f"http://{api_server}:{port}"

session = requests.Session()

"""
from selenium import webdriver

import pytest
import requests

@pytest.fixture
def logged_in_browser(request):
    api_session = requests.post(
        f"http://{api_server}:8080/api/sessions/authorization_url",
        headers=headers,
        data={"redirect_url": f"{web}/sign_in"},
    )
    driver = webdriver.Chrome()
    # driver.add_cookie(cookie)
    yield driver
    driver.quit()
    api_session.close()


def create_entry_test(logged_in_browser):
    driver.get(f"http://{api_server}:8080")
"""


# def test_list(logged_in_browser):
class TestList:
    def list_type(self, mtype: str):
        from python_magnetapi import utils

        return utils.get_list(session, web, headers=headers, mtype=mtype, debug=False)

    def test_material(self):
        _ids = self.list_type("material")
        assert len(_ids) != 0

    def test_part(self):
        _ids = self.list_type("part")
        assert len(_ids) != 0

    def test_magnet(self):
        _ids = self.list_type("magnet")
        assert len(_ids) != 0

    def test_site(self):
        _ids = self.list_type("site")
        assert len(_ids) != 0

    def test_record(self):
        _ids = self.list_type("record")
        assert len(_ids) != 0

    def test_simulation(self):
        _ids = self.list_type("simulation")
        assert len(_ids) != 0


from python_magnetapi.material import create as mat_create
from python_magnetapi.site import create as site_create
from python_magnetapi.site import status as site_status
from python_magnetapi.magnet import create as magnet_create
from python_magnetapi.part import create as part_create
from python_magnetapi.geometry import create as geometry_create
from python_magnetapi.record import create as record_create

ocreate = {
    "material": {"cmd": mat_create, "file": "ma2202802.dat", "object": "testmat3"},
    "part": {"cmd": part_create, "file": "part.dat", "object": "H22121601test"},
    "geometry": {
        "cmd": geometry_create,
        "file": "geometry.dat",
        "object": "H22121601test",
    },
    "magnet": {"cmd": magnet_create, "file": "magnet.dat", "object": "M18110501test"},
    "site": {
        "cmd": site_create,
        "up": site_status,
        "file": "site.dat",
        "object": "M9_M18110501test",
    },
    "record": {"cmd": record_create, "file": "record.dat"},
}


class TestCrud:

    # TODO add check and update entries to ocreate for test automation
    # shall get values from associated file
    # how to enable several files per main key??

    # add params to select either
    # file: single json datastruct
    # xxx: hierachical json datastruct
    def create(self, mtype: str):
        pwd = os.getcwd()
        print(f"cwd={pwd}")
        filename = f"tests/{ocreate[mtype]['file']}"
        print(f"filename={filename}")
        with open(filename, "r") as f:
            data = json.loads(f.read())
        print(f"{mtype}: name={data['name']}", flush=True)

        os.chdir("tests")
        id = ocreate[mtype]["cmd"](
            session, web, headers=headers, data=data, verbose=False, debug=False
        )

        os.chdir(pwd)

        return id

    def delete(self, mtype: str, name: str):
        from python_magnetapi import utils

        ids = utils.get_list(session, web, headers=headers, mtype=mtype, debug=False)
        print(f"id={ids[name]}")

        response = utils.del_object(
            session,
            web,
            headers=headers,
            mtype=mtype,
            id=ids[name],
            verbose=False,
            debug=False,
        )

        ids = utils.get_list(session, web, headers=headers, mtype=mtype, debug=False)
        return name in ids

    def up(self, mtype: str):
        print(f'up={ocreate[mtype]["up"]}', flush=True)
        if mtype != "site":
            return False

        data = {
            "name": "M9_M18110501test",
            "status": "in_operation",
            "date": "2019.03.22 09:27:56",
        }
        isOK = site_status(session, web, headers, data, verbose=True, debug=True)
        return isOK

    def down(self, mtype: str):
        print(f'down={ocreate[mtype]["up"]}', flush=True)
        if mtype != "site":
            return False

        data = {
            "name": "M9_M18110501test",
            "status": "in_stock",
            "date": "2019.03.25 09:27:56",
        }
        isOK = site_status(session, web, headers, data, verbose=True, debug=True)
        return isOK

    def test_create_material(self):
        assert not self.create("material") is None

    def test_create_part(self):
        assert not self.create("part") is None

    def test_create_geometry(self):
        assert not self.create("geometry") is None

    def test_create_magnet(self):
        assert not self.create("magnet") is None

    def test_create_site(self):
        assert not self.create("site") is None

    def test_up_site(self):
        assert self.up("site") is True

    # stop site
    def test_stop_site(self):
        assert self.down("site") is True

    # add new site with previous magnet attached
    # add create record

    """
    def test_delete_site(self):
        print(f'delete {ocreate["site"]["object"]}')
        assert self.delete("site", ocreate["site"]["object"]) == False

    def test_delete_magnet(self):
        print(f'delete {ocreate["magnet"]["object"]}')
        assert self.delete("magnet", ocreate["magnet"]["object"]) == False

    def test_delete_part(self):
        print(f'delete {ocreate["part"]["object"]}')
        assert self.delete("part", ocreate["part"]["object"]) == False

    def test_delete_material(self):
        print(f'delete {ocreate["material"]["object"]}')
        assert self.delete("material", ocreate["material"]["object"]) == False
    """

    # delete record
    # delete site
    # delete magnet
    # delete part
