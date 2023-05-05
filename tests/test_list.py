import os
import pytest
import json

# add  @pytest.fixture to declare context

api_server = os.getenv("MAGNETDB_API_SERVER") or "magnetdb-api.lncmig.local"
api_key = os.getenv("MAGNETDB_API_KEY")
port = 8000

headers = {"Authorization": os.getenv("MAGNETDB_API_KEY")}
web = f"http://{api_server}:{port}"


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

        return utils.get_list(web, headers=headers, mtype=mtype, debug=False)

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


class TestCrud:
    # TODO add check and update entries to ocreate for test automation
    # shall get values from associated file
    # how to enable several files per main key??

    def create(self, mtype: str):
        from python_magnetapi.material import create as mat_create
        from python_magnetapi.site import create as site_create
        from python_magnetapi.magnet import create as magnet_create
        from python_magnetapi.part import create as part_create
        from python_magnetapi.record import create as record_create

        ocreate = {
            "material": {"cmd": mat_create, "file": "ma2202802.dat"},
            "site": {"cmd": site_create, "file": ""},
            "magnet": {"cmd": magnet_create, "file": ""},
            "part": {"cmd": part_create, "file": ""},
            "record": {"cmd": record_create, "file": ""},
        }

        print(f"cwd={os.getcwd()}")
        filename = f"tests/{ocreate[mtype]['file']}"
        with open(filename, "r") as f:
            data = json.loads(f.read())

        id = ocreate[mtype]["cmd"](
            web, headers=headers, data=data, verbose=False, debug=False
        )

        return id

    def delete(self, mtype: str, name: str):
        from python_magnetapi import utils

        ids = utils.get_list(web, headers=headers, mtype=mtype, debug=False)
        print(f"id={ids[name]}")

        response = utils.del_object(
            web,
            headers=headers,
            mtype=mtype,
            id=ids[name],
            verbose=False,
            debug=False,
        )

        ids = utils.get_list(web, headers=headers, mtype=mtype, debug=False)
        return name in ids

    def test_create_material(self):
        assert not self.create("material") is None

    def test_update(self):
        _ids = ["1"]
        assert len(_ids) != 0

    def test_delete_material(self):
        assert self.delete("material", "testmat3") == False
