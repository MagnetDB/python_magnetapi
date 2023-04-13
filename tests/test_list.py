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
    def test_create(self):
        from python_magnetapi.material import create

        print(f"cwd={os.getcwd()}")
        with open("tests/ma2202802.dat", "r") as f:
            data = json.loads(f.read())
        id = create(web, headers=headers, data=data, verbose=False, debug=False)
        assert not id is None

    def test_update(self):
        _ids = ["1"]
        assert len(_ids) != 0

    def test_delete(self):
        from python_magnetapi import utils

        ids = utils.get_list(web, headers=headers, mtype="material", debug=False)
        print(f"id={ids['testmat3']}")
        assert "testmat3" in ids

        response = utils.del_object(
            web,
            headers=headers,
            mtype="material",
            id=ids["testmat3"],
            verbose=False,
            debug=False,
        )
        print(f"response={response}")
        assert not response is None
