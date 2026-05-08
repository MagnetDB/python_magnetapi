"""Utils for interaction with MagnetDB"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import requests

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceConflictError,
    ServerError,
    MagnetAPIException,
)


def get_list(
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    mtype: str = "magnets",
    filters: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    debug: bool = False,
) -> Dict[str, int]:
    """Retrieve list of object IDs for a given resource type.

    Fetches paginated results from the MagnetDB API and returns a dictionary
    mapping object names to their IDs. Optionally filters results based on
    provided attribute-value pairs.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        mtype: Resource type (e.g., "magnet", "part", "site", "simulation")
        filters: Optional dict of attribute:value pairs to filter results
                 e.g., {"status": "active", "type": "helix"}
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        Dictionary mapping object names (str) to their IDs (int)

    Example:
        >>> ids = get_list(session, "https://api.example.com", headers, "magnet")
        >>> print(ids)
        {'M9': 123, 'HL31': 456}
    """
    if verbose:
        print(f"get_list: api_server={api_server}, mtype={mtype}")
        if filters:
            print(f"get_list: filters={filters}")

    # loop over pages
    objects = dict()
    ids = dict()

    n = 1
    while True:
        r = session.get(f"{api_server}/api/{mtype}s?page={n}", headers=headers)
        response = r.json()
        if r.status_code != 200:
            print(response["detail"])
            break
        if debug:
            print(
                f"get_list: {api_server}/api/{mtype}s?page={n}, headers={headers}, res={r.text}"
            )

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
                    session,
                    api_server,
                    headers,
                    resource_id,
                    resource_type,
                    verbose,
                    debug,
                )
                object["name"] = (
                    f"{resource['name']}: {object['method']}/{object['geometry']}/{object['model']}/{object['cooling']}"
                )
            objects[object["name"]] = object

        # increment page
        n += 1

        # break if last page is reached
        if current_page == last_page:
            break

    for object in objects:
        # Apply filters if provided
        if filters:
            matches = True
            for attr, value in filters.items():
                # Check if attribute exists and matches the filter value
                if attr not in objects[object] or str(objects[object][attr]) != str(
                    value
                ):
                    matches = False
                    break
            if not matches:
                continue

        if debug:
            print(
                f"{mtype.upper()}: {objects[object]['name']} (id:{objects[object]['id']})"
            )
        ids[objects[object]["name"]] = objects[object]["id"]

    return ids


def get_object(
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    id: int,
    mtype: str = "magnet",
    verbose: bool = False,
    debug: bool = False,
) -> Optional[Dict[str, Any]]:
    """Retrieve a single object by ID from the API.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        id: Unique identifier of the object to retrieve
        mtype: Resource type (e.g., "magnet", "part", "site")
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        Dictionary containing the object data, or None if request fails
    """
    if verbose:
        print(f"get_object: api_server={api_server}, mtype={mtype}, id={id}")

    r = session.get(f"{api_server}/api/{mtype}s/{id}", headers=headers)
    response = r.json()

    if r.status_code != 200:
        print(f"get_object: {api_server}/api/{mtype}s/{id}")
        print(response["detail"])
        return None
    else:
        return response


def create_object(
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    mtype: str = "magnet",
    data: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    debug: bool = False,
) -> int:
    """Create a new object in the MagnetDB API.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        mtype: Resource type (e.g., "magnet", "part", "simulation", "material")
        data: Dictionary containing object data to create
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        ID of the newly created object

    Raises:
        AuthenticationError: If authentication fails (401)
        AuthorizationError: If user lacks permission (403)
        ResourceConflictError: If resource already exists (409)
        ServerError: If server error occurs (5xx)
        MagnetAPIException: For other API errors
    """
    if data is None:
        data = {}
    if verbose:
        print(f"create_object: api_server={api_server}, mtype={mtype}, data={data}")

    web = f"{api_server}/api/{mtype}s"
    r = None
    if mtype in ["attachment"]:
        r = session.post(web, files=data, headers=headers)
    elif mtype in ["simulation", "material", "record"]:
        r = session.post(web, json=data, headers=headers)
    else:
        r = session.post(web, data=data, headers=headers)

    response = r.json()
    if r.status_code != 200:
        detail = response.get("detail", "Unknown error")
        if r.status_code == 401:
            raise AuthenticationError(
                f"Authentication failed while creating {mtype}",
                status_code=401,
                url=web,
            )
        elif r.status_code == 403:
            raise AuthorizationError(
                f"Not authorized to create {mtype} objects", status_code=403, url=web
            )
        elif r.status_code == 409:
            raise ResourceConflictError(
                f"Conflict while creating {mtype}: {detail}", status_code=409, url=web
            )
        elif r.status_code >= 500:
            raise ServerError(
                f"Server error while creating {mtype}: {detail}",
                status_code=r.status_code,
                url=web,
            )
        else:
            raise MagnetAPIException(
                f"Failed to create {mtype}: {detail}",
                status_code=r.status_code,
                url=web,
            )

    if debug:
        print(
            f"create_object: {web}, {mtype.upper()} created: \n{json.dumps(response, indent=4)}"
        )

    return response["id"]


def update_object(
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    id: int,
    mtype: str = "magnet",
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    debug: bool = False,
) -> Optional[Dict[str, Any]]:
    """Update an existing object in the MagnetDB API.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        id: Unique identifier of the object to update
        mtype: Resource type (e.g., "magnet", "part", "site")
        data: Dictionary containing fields to update
        files: Dictionary containing files to upload (currently unused)
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        Updated object data as dictionary, or None if request fails
    """
    if data is None:
        data = {}
    if files is None:
        files = {}
    if verbose:
        print(f"update_object: api_server={api_server}, mtype={mtype}, data={data}")

    web = f"{api_server}/api/{mtype}s/{id}"
    r = session.patch(web, data=data, headers=headers)

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
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    id: int,
    mtype: str = "magnet",
    dtype: str = "part",
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    debug: bool = False,
) -> Optional[Dict[str, Any]]:
    """Update an object in an associative table (many-to-many relationship).

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        id: ID of the parent object (e.g., magnet ID)
        mtype: Parent resource type (e.g., "magnet")
        dtype: Related resource type (e.g., "part")
        data: Dictionary containing fields to update in the association
        files: Dictionary containing files to upload (currently unused)
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        Updated association data as dictionary, or None if request fails
    """
    if data is None:
        data = {}
    if files is None:
        files = {}
    if verbose:
        print(
            f"update_associative_object: api_server={api_server}, mtype={mtype}, data={data}"
        )

    web = f"{api_server}/api/{mtype}s/{id}/{dtype}s"
    r = session.patch(web, data=data, headers=headers)

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
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    mtype: str = "magnet",
    id: Optional[int] = None,
    verbose: bool = False,
    debug: bool = False,
) -> Optional[Dict[str, Any]]:
    """Delete an object from the MagnetDB API.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        mtype: Resource type (e.g., "magnet", "part", "site")
        id: Unique identifier of the object to delete
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        API response as dictionary, or None if request fails
    """
    if verbose:
        print(f"del_object: api_server={api_server}, mtype={mtype}, id={id}")
    r = session.delete(
        f"{api_server}/api/{mtype}s/{id}", data={"id": id}, headers=headers
    )
    response = r.json()
    if r.status_code != 200:
        print(response["detail"])
        return None

    print(response)
    return response


def add_data_to_object(
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    id: int,
    data: Dict[str, Any],
    mtype: str = "magnet",
    dtype: str = "part",
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Add data to an object via POST to an associative endpoint.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        id: ID of the parent object
        data: Dictionary containing data to add
        mtype: Parent resource type (e.g., "magnet")
        dtype: Related resource type (e.g., "part")
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        None
    """
    if verbose:
        print(
            f"add_data_to_object: api_server={api_server}, mtype={mtype}, id={id}, dtype={dtype}, data={data}"
        )

    print(f"add_data_to_object: {api_server}/api/{mtype}s/{id}/{dtype}s")
    r = session.post(
        f"{api_server}/api/{mtype}s/{id}/{dtype}s",
        data=data,
        headers=headers,
    )
    print(f"add_data_to_object: r={r}")
    response = r.json()
    print(f"add_data_to_object: response={response}")
    if r.status_code != 200:
        print(response["detail"])
        return None
    pass


def add_files_to_object(
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    id: int,
    mtype: str = "part",
    dtype: str = "geometrie",
    files: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Upload files to an object via POST to an associative endpoint.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        id: ID of the parent object
        mtype: Parent resource type (e.g., "part")
        dtype: Related resource type (e.g., "geometrie")
        files: Dictionary containing file data to upload
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        None
    """
    if files is None:
        files = {}
    if verbose:
        print(
            f"add_files_to_object: api_server={api_server}, mtype={mtype}, id={id}, dtype={dtype}, files={files}"
        )

    r = session.post(
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
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    id: int,
    mtype: str = "part",
    dtype: str = "geometrie",
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Upload both data and files to an object via POST.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        id: ID of the parent object
        mtype: Parent resource type (e.g., "part")
        dtype: Related resource type (e.g., "geometrie")
        data: Dictionary containing data to upload
        files: Dictionary containing file data to upload
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        None
    """
    if data is None:
        data = {}
    if files is None:
        files = {}
    if verbose:
        print(
            f"add_files_to_object: api_server={api_server}, mtype={mtype}, id={id}, dtype={dtype}, files={files}"
        )

    r = session.post(
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
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    id: int,
    mtype: str = "magnet",
    otype: str = "record",
    verbose: bool = False,
    debug: bool = False,
) -> Optional[List[Dict[str, Any]]]:
    """Retrieve history of related objects (records or sites) for a given object.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        id: ID of the parent object
        mtype: Parent resource type ("part", "magnet", or "site")
        otype: Related object type ("record" or "site")
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        List of related objects as dictionaries, empty list if mtype not supported,
        or None if request fails
    """
    if verbose:
        print(
            f"get_history: api_server={api_server}, mtype={mtype}, otype={otype}, id={id}"
        )

    r = session.get(f"{api_server}/api/{mtype}s/{id}", headers=headers)
    response = r.json()
    if r.status_code != 200:
        print(
            f"get_history: api_server={api_server}, mtype={mtype}, otype={otype}, id={id} response={response['detail']}"
        )
        return None

    if mtype in ["part", "magnet", "site"]:
        r = session.get(f"{api_server}/api/{mtype}s/{id}/{otype}s", headers=headers)
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
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    oid: int,
    mtype: str = "magnet",
    verbose: bool = False,
    debug: bool = False,
) -> Optional[Dict[str, Any]]:
    """Retrieve metadata attached to an object.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        oid: Unique identifier of the object
        mtype: Resource type (e.g., "magnet", "part")
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        Dictionary containing metadata, or None if request fails
    """
    if verbose:
        print(f"get_data: api_server={api_server}, mtype={mtype}, id={oid}")

    r = session.get(f"{api_server}/api/{mtype}s/{oid}/mdata", headers=headers)
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
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    data: Dict[str, Any],
    mtype: str = "magnet",
    verbose: bool = False,
    debug: bool = False,
) -> Optional[Dict[str, Any]]:
    """Send form data to create an object via POST.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        data: Dictionary containing form data to post
        mtype: Resource type (e.g., "magnet", "part")
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        API response as dictionary, or None if request fails
    """
    if verbose:
        print(f"post_data: api_server={api_server}, mtype={mtype}, data={data}")

    r = session.post(f"{api_server}/api/{mtype}s", data=data, headers=headers)
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
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    data: Dict[str, Any],
    mtype: str = "magnet",
    verbose: bool = False,
    debug: bool = False,
) -> Dict[str, Any]:
    """Send JSON data to create an object via POST.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        data: Dictionary containing JSON data to post
        mtype: Resource type (e.g., "magnet", "simulation", "material")
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        API response as dictionary

    Raises:
        AuthenticationError: If authentication fails (401)
        AuthorizationError: If user lacks permission (403)
        ResourceConflictError: If resource already exists (409)
        ServerError: If server error occurs (5xx)
        MagnetAPIException: For other API errors
    """
    if verbose:
        print(f"post_json: api_server={api_server}, mtype={mtype}, data={data}")

    r = session.post(f"{api_server}/api/{mtype}s", json=data, headers=headers)
    response = r.json()
    if r.status_code != 200:
        detail = response.get("detail", "Unknown error")
        if r.status_code == 401:
            raise AuthenticationError(
                f"Authentication failed while creating {mtype}",
                status_code=401,
                url=f"{api_server}/api/{mtype}s",
            )
        elif r.status_code == 403:
            raise AuthorizationError(
                f"Not authorized to create {mtype} objects",
                status_code=403,
                url=f"{api_server}/api/{mtype}s",
            )
        elif r.status_code == 409:
            raise ResourceConflictError(
                f"Conflict while creating {mtype}: {detail}",
                status_code=409,
                url=f"{api_server}/api/{mtype}s",
            )
        elif r.status_code >= 500:
            raise ServerError(
                f"Server error while creating {mtype}: {detail}",
                status_code=r.status_code,
                url=f"{api_server}/api/{mtype}s",
            )
        else:
            raise MagnetAPIException(
                f"Failed to create {mtype}: {detail}",
                status_code=r.status_code,
                url=f"{api_server}/api/{mtype}s",
            )

    if debug:
        print(f"post_json: response={response}")
    return response


def post_file(
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    data: Dict[str, Any],
    mtype: str = "magnet",
    verbose: bool = False,
    debug: bool = False,
) -> Dict[str, Any]:
    """Upload files to create an object via POST.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        data: Dictionary containing file data to upload
        mtype: Resource type (e.g., "attachment")
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        API response as dictionary

    Raises:
        AuthenticationError: If authentication fails (401)
        AuthorizationError: If user lacks permission (403)
        ServerError: If server error occurs (5xx)
        MagnetAPIException: For other API errors
    """
    if verbose:
        print(f"post_file: api_server={api_server}, mtype={mtype}, files={data}")

    print(f"post_file: files={data}")
    r = session.post(f"{api_server}/api/{mtype}s", files=data, headers=headers)
    response = r.json()
    print(f"post_file: response={response}")
    if r.status_code != 200:
        detail = response.get("detail", "Unknown error")
        if r.status_code == 401:
            raise AuthenticationError(
                f"Authentication failed while uploading file for {mtype}",
                status_code=401,
                url=f"{api_server}/api/{mtype}s",
            )
        elif r.status_code == 403:
            raise AuthorizationError(
                f"Not authorized to upload files for {mtype} objects",
                status_code=403,
                url=f"{api_server}/api/{mtype}s",
            )
        elif r.status_code >= 500:
            raise ServerError(
                f"Server error while uploading file for {mtype}: {detail}",
                status_code=r.status_code,
                url=f"{api_server}/api/{mtype}s",
            )
        else:
            raise MagnetAPIException(
                f"Failed to upload file for {mtype}: {detail}",
                status_code=r.status_code,
                url=f"{api_server}/api/{mtype}s",
            )

    if debug:
        print(f"post_file: response={response}")
    return response


def download(
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    attach: str,
    wd: str = "",
    verbose: bool = False,
    debug: bool = False,
) -> Optional[str]:
    """Download an attachment file from the MagnetDB API.

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        attach: Attachment ID or identifier
        wd: Working directory where file should be saved (default: current directory)
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        Filename of the downloaded file, or None if download fails
    """
    import os

    if verbose:
        print(f"download: api_server={api_server}, attach={attach}")

    r = session.get(f"{api_server}/api/attachments/{attach}/download", headers=headers)
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
    with open(filename, "wb") as file:
        file.write(r.content)

    os.chdir(cwd)
    return filename


def upload(
    session: requests.Session,
    api_server: str,
    headers: Dict[str, str],
    attach: str,
    verbose: bool = False,
    debug: bool = False,
) -> None:
    """Upload a file to the MagnetDB API.

    Note: This function is currently not implemented (stub).

    Args:
        session: Active requests session with authentication
        api_server: Base URL of the API server
        headers: HTTP request headers including authentication token
        attach: File path or identifier to upload
        verbose: If True, print informational messages
        debug: If True, print detailed debugging information

    Returns:
        None
    """
    if verbose:
        print(f"upload: api_server={api_server}, attach={attach}")
    pass
