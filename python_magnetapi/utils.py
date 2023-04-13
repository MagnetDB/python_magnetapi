"""
Utils for interaction with MagnetDB
"""

import json
import requests
import re


def get_list(
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
        print(f"get_list: api_server={api_server}, mtype={mtype}")

    # loop over pages
    objects = dict()
    ids = dict()

    n = 1
    while True:
        r = requests.get(f"{api_server}/api/{mtype}s?page={n}", headers=headers)
        if r.status_code != 200:
            print(response["detail"])
            break
        if debug:
            print(
                f"get_list: {api_server}/api/{mtype}s?page={n}, headers={headers}, res={r.text}"
            )
        response = r.json()

        # check r.json() pages max
        current_page = response["current_page"]
        last_page = response["last_page"]

        # get object list per page
        _page_dict = response["items"]
        if debug:
            print(f"_page_dict={_page_dict}")
        for object in _page_dict:
            if mtype == "simulation":
                print(f"object: {object}")
                resource_type = object["resource_type"][:-1]
                resource_id = object["resource_id"]
                resource = get_object(
                    api_server, headers, resource_id, resource_type, verbose, debug
                )
                object[
                    "name"
                ] = f"{resource['name']}: {object['method']}/{object['geometry']}/{object['model']}/{object['cooling']}"
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


def get_object(
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
        print(f"get_object: api_server={api_server}, mtype={mtype}, id={id}")

    r = requests.get(f"{api_server}/api/{mtype}s/{id}", headers=headers)
    response = r.json()

    if r.status_code != 200:
        print(f"get_object: {api_server}/api/{mtype}s/{id}")
        print(response["detail"])
        return None
    else:
        return response


def create_object(
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
    if verbose:
        print(f"create_object: api_server={api_server}, mtype={mtype}, data={data}")

    web = f"{api_server}/api/{mtype}s"
    r = None
    if mtype in ["attachment"]:
        r = requests.post(web, files=data, headers=headers)
    elif mtype in ["simulation", "material", "record"]:
        r = requests.post(web, json=data, headers=headers)
    else:
        r = requests.post(web, data=data, headers=headers)

    response = r.json()
    if r.status_code != 200:
        print(
            f"create_object: api_server={web}, mtype={mtype}, response={response['detail']}"
        )
        return None

    if debug:
        print(
            f"create_object: {web}, {mtype.upper()} created: \n{json.dumps(response, indent=4)}"
        )

    return response["id"]


def update_object(
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "magnet",
    data: dict = {},
    files: dict = {},
    verbose: bool = False,
    debug: bool = False,
):
    """
    update an object
    """
    if verbose:
        print(f"update_object: api_server={api_server}, mtype={mtype}, data={data}")

    web = f"{api_server}/api/{mtype}s/{id}"
    r = requests.patch(web, data=data, headers=headers)

    response = r.json()
    if r.status_code != 200:
        print(
            f"update_object: api_server={web}, mtype={mtype}, response={response['detail']}"
        )
        return None

    if debug:
        print(
            f"update_object: {web}, {mtype.upper()} created: \n{json.dumps(response, indent=4)}"
        )

    return response


def update_associative_object(
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "magnet",
    dtype: str = "part",
    data: dict = {},
    files: dict = {},
    verbose: bool = False,
    debug: bool = False,
):
    """
    update an object in associative table
    """
    if verbose:
        print(
            f"update_associative_object: api_server={api_server}, mtype={mtype}, data={data}"
        )

    web = f"{api_server}/api/{mtype}s/{id}/{dtype}s"
    r = requests.patch(web, data=data, headers=headers)

    response = r.json()
    if r.status_code != 200:
        print(
            f"update_associative_object: api_server={web}, mtype={mtype}, response={response['detail']}"
        )
        return None

    if debug:
        print(
            f"update_associative_object: {web}, {mtype.upper()} created: \n{json.dumps(response, indent=4)}"
        )

    return response


def del_object(
    api_server: str,
    headers: dict,
    mtype: str = "magnet",
    id: int = None,
    verbose: bool = False,
    debug: bool = False,
):
    """
    delete an object given its id
    """
    if verbose:
        print(f"del_object: api_server={api_server}, mtype={mtype}, id={id}")
    r = requests.delete(
        f"{api_server}/api/{mtype}s/{id}", data={"id": id}, headers=headers
    )
    response = r.json()
    if r.status_code != 200:
        print(response["detail"])
        return None

    print(response)
    return response


def add_data_to_object(
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "magnet",
    dtype: str = "part",
    data: dict = {},
    files: dict() = {},
    verbose: bool = False,
    debug: bool = False,
):
    """
    add data to an object
    """
    if verbose:
        print(
            f"add_data_to_object: api_server={api_server}, mtype={mtype}, id={id}, dtype={dtype}, data={data}"
        )

    r = requests.post(
        f"{api_server}/api/{mtype}s/{id}/{dtype}s",
        json=data,
        headers=headers,
    )
    response = r.json()
    if r.status_code != 200:
        print(response["detail"])
        return None
    pass


def add_files_to_object(
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "part",
    dtype: str = "geometrie",
    files: dict = {},
    verbose: bool = False,
    debug: bool = False,
):
    """
    add files to an object
    """
    if verbose:
        print(
            f"add_files_to_object: api_server={api_server}, mtype={mtype}, id={id}, dtype={dtype}, files={files}"
        )

    r = requests.post(
        f"{api_server}/api/{mtype}s/{id}/{dtype}s",
        files=files,
        headers=headers,
    )
    response = r.json()
    if r.status_code != 200:
        print(response["detail"])
        return None
    pass


def add_data_files_to_object(
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "part",
    dtype: str = "geometrie",
    data: dict = {},
    files: dict = {},
    verbose: bool = False,
    debug: bool = False,
):
    """
    add data and files to an object
    """
    if verbose:
        print(
            f"add_files_to_object: api_server={api_server}, mtype={mtype}, id={id}, dtype={dtype}, files={files}"
        )

    r = requests.post(
        f"{api_server}/api/{mtype}s/{id}/{dtype}s",
        data=data,
        files=files,
        headers=headers,
    )
    response = r.json()
    if r.status_code != 200:
        print(response["detail"])
        return None
    pass


def get_history(
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
            f"get_history: api_server={api_server}, mtype={mtype}, otype={otype}, id={id}"
        )

    r = requests.get(f"{api_server}/api/{mtype}s/{id}", headers=headers)
    response = r.json()
    if r.status_code != 200:
        print(
            f"get_history: api_server={api_server}, mtype={mtype}, otype={otype}, id={id} response={response['detail']}"
        )
        return None

    if mtype in ["part", "magnet", "site"]:
        r = requests.get(f"{api_server}/api/{mtype}s/{id}/{otype}s", headers=headers)
        response = r.json()
        if r.status_code != 200:
            print(f"{api_server}/api/{mtype}s/{id}/{otype}s")
            print(
                f"get_history: api_server={api_server}, mtype={mtype}, otype={otype}, id={id} response={response['detail']}"
            )
            return None
        return response[f"{otype}s"]

    return []


def get_data(
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
        print(f"get_data: api_server={api_server}, mtype={mtype}, id={oid}")

    r = requests.get(f"{api_server}/api/{mtype}s/{oid}/mdata", headers=headers)
    response = r.json()
    if r.status_code != 200:
        print(
            f"get_data: api_server={api_server}/api/{mtype}s/{oid}/mdata, mtype={mtype}, id={oid} response={response['detail']}"
        )
        return None

    if debug:
        print(f"get_data: response={response}")
    return response


def post_data(
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
        print(f"post_data: api_server={api_server}, mtype={mtype}, data={data}")

    r = requests.post(f"{api_server}/api/{mtype}s", data=data, headers=headers)
    response = r.json()
    if r.status_code != 200:
        print(
            f"post_data: api_server={api_server}/api/{mtype}s, mtype={mtype}, response={response['detail']}"
        )
        return None

    if debug:
        print(f"post_data: response={response}")
    return response


def post_json(
    api_server: str,
    headers: dict,
    data: dict,
    mtype: str = "magnet",
    verbose: bool = False,
    debug: bool = False,
):
    """
    send json to create mtype object

    """
    if verbose:
        print(f"post_json: api_server={api_server}, mtype={mtype}, data={data}")

    r = requests.post(f"{api_server}/api/{mtype}s", json=data, headers=headers)
    response = r.json()
    if r.status_code != 200:
        print(
            f"post_json: api_server={api_server}/api/{mtype}s, mtype={mtype}, response={response['detail']}"
        )
        return None

    if debug:
        print(f"post_json: response={response}")
    return response


def post_file(
    api_server: str,
    headers: dict,
    data: dict,
    mtype: str = "magnet",
    verbose: bool = False,
    debug: bool = False,
):
    """
    send data to upload

    """
    if verbose:
        print(f"post_file: api_server={api_server}, mtype={mtype}, files={data}")

    print(f"post_file: files={data}")
    r = requests.post(f"{api_server}/api/{mtype}s", files=data, headers=headers)
    response = r.json()
    print(f"post_file: response={response}")
    if r.status_code != 200:
        print(
            f"post_file: api_server={api_server}/api/{mtype}s, mtype={mtype}, response={response['detail']}"
        )
        return None

    if debug:
        print(f"post_file: response={response}")
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
