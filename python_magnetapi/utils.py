"""
Utils for interaction with MagnetDB
"""

import json
import requests
import re


def getlist(
    api_server: str,
    headers: dict,
    mtype: str = "magnets",
    verbose: bool = False,
    debug: bool = False,
) -> dict():
    """
    return list of ids for selected tpye
    """
    if verbose:
        print(f"getlist: api_server={api_server}, mtype={mtype}")

    # loop over pages
    objects = dict()
    ids = dict()

    n = 1
    while True:
        r = requests.get(f"{api_server}/api/{mtype}s?page={n}", headers=headers)
        if r.status_code != 200:
            print(response["detail"])
            break

        response = r.json()

        # check r.json() pages max
        current_page = response["current_page"]
        last_page = response["last_page"]

        # get object list per page
        _page_dict = response["items"]
        if debug:
            print(f"_page_dict={_page_dict}")
        for object in _page_dict:
            objects[object["name"]] = object

        # increment page
        n += 1

        # break if last page is reached
        if current_page == last_page:
            break

    for object in objects:
        if debug:
            print(
                f"{mtype.upper()}: {objects[object]['name']} (id:{objects[object]['id']})"
            )
        ids[objects[object]["name"]] = objects[object]["id"]

    return ids


def getobject(
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "magnet",
    verbose: bool = False,
    debug: bool = False,
):
    """
    return id of an object with name == name
    """
    if verbose:
        print(f"getobject: api_server={api_server}, mtype={mtype}, id={id}")

    r = requests.get(f"{api_server}/api/{mtype}s/{id}", headers=headers)
    response = r.json()

    if r.status_code != 200:
        print(f"getobject: {api_server}/api/{mtype}s/{id}")
        print(response["detail"])
        return None
    else:
        return response


def createobject(
    api_server: str,
    headers: dict,
    mtype: str = "magnet",
    data: dict = {},
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """
    create an object and return its id
    """
    print(f"createobject: api_server={api_server}, mtype={mtype}, data={data}")

    r = requests.post(f"{api_server}/api/{mtype}s", json=data, headers=headers)
    response = r.json()
    if r.status_code != 200:
        print(response["detail"])
        return None
    else:
        if debug:
            print(f"{mtype.upper()} created: \n{json.dumps(response, indent=4)}")
        return response["id"]


def addtoobject(
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "magnet",
    data: dict = {},
    files: dict() = {},
    verbose: bool = False,
    debug: bool = False,
):
    """
    add xx to an object
    """
    if verbose:
        print(
            f"addtoobject: api_server={api_server}, mtype={mtype}, id={id}, data={data}, files={files}"
        )

    r = requests.post(
        f"{api_server}/api/{mtype}s/{id}/geometries",
        json=data,
        files=files,
        headers=headers,
    )
    response = r.json()
    if r.status_code != 200:
        print(response["detail"])
        return None
    pass


def gethistory(
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "magnet",
    otype="record",
    verbose: bool = False,
    debug: bool = False,
):
    """
    return list of otype ids attached to object id

    otype = site|record
    """
    if verbose:
        print(
            f"gethistory: api_server={api_server}, mtype={mtype}, otype={otype}, id={id}"
        )

    r = requests.get(f"{api_server}/api/{mtype}s/{id}", headers=headers)
    response = r.json()
    if r.status_code != 200:
        print(
            f"gethistory: api_server={api_server}, mtype={mtype}, otype={otype}, id={id} response={response['detail']}"
        )
        return None

    if mtype in ["part", "magnet", "site"]:
        r = requests.get(f"{api_server}/api/{mtype}s/{id}/{otype}s", headers=headers)
        response = r.json()
        if r.status_code != 200:
            print(f"{api_server}/api/{mtype}s/{id}/{otype}s")
            print(
                f"gethistory: api_server={api_server}, mtype={mtype}, otype={otype}, id={id} response={response['detail']}"
            )
            return None
        return response[f"{otype}s"]

    return []


def getdata(
    api_server: str,
    headers: dict,
    oid: int,
    mtype: str = "magnet",
    verbose: bool = False,
    debug: bool = False,
):
    """
    return data attached to mtype object with oid

    """
    if verbose:
        print(f"getdata: api_server={api_server}, mtype={mtype}, id={oid}")

    r = requests.get(f"{api_server}/api/{mtype}s/{oid}/mdata", headers=headers)
    response = r.json()
    if r.status_code != 200:
        print(
            f"getdata: api_server={api_server}/api/{mtype}s/{oid}/mdata, mtype={mtype}, id={oid} response={response['detail']}"
        )
        return None

    if debug:
        print(f"getdata: response={response}")
    return response


def postdata(
    api_server: str,
    headers: dict,
    data: dict,
    mtype: str = "magnet",
    verbose: bool = False,
    debug: bool = False,
):
    """
    send data to create mtype object

    """
    if verbose:
        print(f"postdata: api_server={api_server}, mtype={mtype}, data={data}")

    print(f"postdata: json={data}")
    r = requests.post(f"{api_server}/api/{mtype}s", json=data, headers=headers)
    response = r.json()
    print(f"postdata: response={response}")
    if r.status_code != 200:
        print(
            f"postdata: api_server={api_server}/api/{mtype}s, mtype={mtype}, response={response['detail']}"
        )
        return None

    if debug:
        print(f"postdata: response={response}")
    return response


def download(
    api_server: str,
    headers: dict,
    attach: str,
    wd: str = "",
    verbose: bool = False,
    debug: bool = False,
):
    """
    download file
    """
    import os

    if verbose:
        print(f"download: api_server={api_server}, attach={attach}")

    r = requests.get(f"{api_server}/api/attachments/{attach}/download", headers=headers)
    if r.status_code != 200:
        # print(f"download: api_server={api_server}, attach={attach} response={r.status_code}")
        return None

    cwd = os.getcwd()
    if wd:
        os.chdir(wd)

    filename = list(
        re.finditer(
            r"filename=\"(.+)\"", r.headers["content-disposition"], re.MULTILINE
        )
    )[0].group(1)
    with open(filename, "w+") as file:
        file.write(r.text)

    os.chdir(cwd)
    return filename


def upload(
    api_server: str,
    headers: dict,
    attach: str,
    verbose: bool = False,
    debug: bool = False,
):
    """
    upload file
    """
    if verbose:
        print(f"upload: api_server={api_server}, attach={attach}")
    pass
