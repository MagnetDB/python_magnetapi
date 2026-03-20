"""
Utils for interaction with MagnetDB
"""

import json
import logging
import re

import requests

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceConflictError,
    ServerError,
    MagnetAPIException,
)

logger = logging.getLogger(__name__)


def setup_logging(level: str = "WARNING", log_file: str = None) -> None:
    """Configure the root logger for python_magnetapi.

    Args:
        level: Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional file path to write logs to in addition to stderr.
    """
    numeric_level = getattr(logging, f"{level.upper()}", logging.WARNING)
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=handlers,
    )


def get_list(
    session: requests.Session,
    api_server: str,
    headers: dict,
    mtype: str = "magnets",
    filters: dict = None,
) -> dict:
    """
    return list of ids for selected type

    Args:
        session: requests session
        api_server: API server URL
        headers: request headers
        mtype: object type (magnet, part, site, etc.)
        filters: dict of attribute:value pairs to filter results
                 e.g., {"status": "active", "type": "helix"}

    Returns:
        dict: mapping of object names to IDs (filtered if filters provided)
    """
    logger.info(f"get_list: api_server={api_server}, mtype={mtype}")
    if filters:
        logger.info(f"get_list: filters={filters}")

    # loop over pages
    objects = dict()
    ids = dict()

    n = 1
    while True:
        r = session.get(f"{api_server}/api/{mtype}s?page={n}", headers=headers)
        response = r.json()
        if r.status_code != 200:
            logger.error(response["detail"])
            break
        logger.debug(
            f"get_list: {api_server}/api/{mtype}s?page={n}, headers={headers}, res={r.text}"
        )

        # check r.json() pages max
        current_page = response["current_page"]
        last_page = response["last_page"]

        # get object list per page
        _page_dict = response["items"]
        logger.debug(f"_page_dict={_page_dict}")
        for object in _page_dict:
            if mtype == "simulation":
                logger.debug(f"object: {object}")
                resource_type = object["resource_type"][:-1]
                resource_id = object["resource_id"]
                resource = get_object(
                    session,
                    api_server,
                    headers,
                    resource_id,
                    resource_type,
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

        logger.debug(
            f"{mtype.upper()}: {objects[object]['name']} (id:{objects[object]['id']})"
        )
        ids[objects[object]["name"]] = objects[object]["id"]

    return ids


def get_object(
    session: requests.Session,
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "magnet",
) -> dict | None:
    """Return the API response dict for a single object.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        id: object ID
        mtype: resource type (magnet, part, site, etc.)

    Returns:
        Object data dict, or None if the request failed.
    """
    logger.info(f"get_object: api_server={api_server}, mtype={mtype}, id={id}")

    r = session.get(f"{api_server}/api/{mtype}s/{id}", headers=headers)
    response = r.json()

    if r.status_code != 200:
        logger.error(f"get_object: {api_server}/api/{mtype}s/{id}: {response['detail']}")
        return None
    else:
        return response


def get_fk_id(obj: dict, field: str) -> int | None:
    """
    Extract the integer ID for a direct/forward ForeignKey field from a
    MagnetDB API response dict (as returned by get_object).

    Django serializes a ForeignKey named `material` as the column `material_id`
    (an integer), not as a nested object.  Checks in order:
      1. "{field}_id" key  — standard Django column name (primary form)
      2. "{field}" key holding an int
      3. "{field}" key holding a dict with "id" (defensive fallback)

    For reverse FK / many-to-many relations (e.g. parts on a magnet) the
    related objects are NOT in the get_object response.
    Use get_parts_for_magnet() or an equivalent nested-endpoint helper instead.
    """
    fk_col = f"{field}_id"
    if fk_col in obj:
        return obj[fk_col]
    value = obj.get(field)
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        return value.get("id")
    return None


def get_parts_for_magnet(
    session: requests.Session,
    api_server: str,
    headers: dict,
    magnet_id: int,
) -> list[dict]:
    """
    Return the full Part objects associated with a magnet.

    Calls GET /api/magnets/{magnet_id}/parts (must exist in magnetdb).
    The endpoint may return either:
    - a bare array of Part objects directly, or
    - a bare array of MagnetPart join rows each containing a `part_id` field.

    In the join-row case each part is fetched individually via get_object.
    Returns a list of Part dicts (same structure as get_object(mtype="part")).
    """
    logger.info(f"get_parts_for_magnet: api_server={api_server}, magnet_id={magnet_id}")

    r = session.get(f"{api_server}/api/magnets/{magnet_id}/parts", headers=headers)
    if r.status_code != 200:
        logger.error(f"get_parts_for_magnet: {r.status_code} for magnet {magnet_id}")
        return []

    rows = r.json()
    logger.debug(f"get_parts_for_magnet: rows={rows}")

    if not rows:
        return []

    logger.info(
        f"get_parts_for_magnet: {len(rows['parts'])} parts found for magnet {magnet_id}"
    )
    logger.debug(
        f"get_parts_for_magnet: {[magnet_part.get('part').get('id') for magnet_part in rows['parts']]} parts found for magnet {magnet_id}"
    )

    parts = []

    seen = set()
    for i, magnet_part in enumerate(rows["parts"]):
        part_id = magnet_part.get("part").get("id")
        if part_id is None or part_id in seen:
            continue
        try:
            logger.debug(f"get_parts_for_magnet: part[{i}] = id={part_id}")
            seen.add(part_id)
            part = get_object(
                session,
                api_server,
                headers,
                part_id,
                mtype="part",
            )
            logger.debug(
                f"name={part.get('name')}, type={part.get('type')}, material={part.get('material').get('name') if part.get('material') else None}"
            )
            if part:
                parts.append(part)
        except Exception as e:
            logger.error(f"Error fetching part with id {part_id}: {e}")

    return parts


def get_magnets_for_site(
    session: requests.Session,
    api_server: str,
    headers: dict,
    site_id: int,
) -> list[dict]:
    """
    Return the full Magnet objects associated with a site.

    Calls GET /api/sites/{site_id}/magnets (must exist in magnetdb).
    The endpoint returns a dict with a `site_magnets` key, each entry
    containing a `magnet_id` field and a nested `magnet` object.

    Each magnet is fetched individually via get_object to obtain the full
    representation.
    Returns a list of Magnet dicts (same structure as get_object(mtype="magnet")).
    """
    logger.info(f"get_magnets_for_site: api_server={api_server}, site_id={site_id}")

    r = session.get(f"{api_server}/api/sites/{site_id}/magnets", headers=headers)
    if r.status_code != 200:
        logger.error(f"get_magnets_for_site: {r.status_code} for site {site_id}")
        return []

    rows = r.json()
    logger.debug(f"get_magnets_for_site: rows={rows}")

    if not rows:
        return []

    site_magnets = rows.get("site_magnets", [])
    logger.info(
        f"get_magnets_for_site: {len(site_magnets)} magnets found for site {site_id}"
    )
    logger.debug(
        f"get_magnets_for_site: {[sm.get('magnet', {}).get('id') for sm in site_magnets]} magnets found for site {site_id}"
    )

    magnets = []
    seen = set()
    for i, site_magnet in enumerate(site_magnets):
        magnet_id = site_magnet.get("magnet", {}).get("id") or site_magnet.get("magnet_id")
        if magnet_id is None or magnet_id in seen:
            continue
        try:
            logger.debug(f"get_magnets_for_site: magnet[{i}] = id={magnet_id}")
            seen.add(magnet_id)
            magnet = get_object(
                session,
                api_server,
                headers,
                magnet_id,
                mtype="magnet",
            )
            logger.debug(f"name={magnet.get('name') if magnet else None}")
            if magnet:
                magnets.append(magnet)
        except Exception as e:
            logger.error(f"Error fetching magnet with id {magnet_id}: {e}")

    return magnets


def create_object(
    session: requests.Session,
    api_server: str,
    headers: dict,
    mtype: str = "magnet",
    data: dict = {},
) -> int:
    """
    create an object and return its id
    """
    logger.info(f"create_object: api_server={api_server}, mtype={mtype}, data={data}")

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

    logger.debug(
        f"create_object: {web}, {mtype.upper()} created: \n{json.dumps(response, indent=4)}"
    )

    return response["id"]


def update_object(
    session: requests.Session,
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "magnet",
    data: dict = {},
    files: dict = {},
) -> dict | None:
    """Update an existing object via PATCH.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        id: object ID to update
        mtype: resource type (magnet, part, site, etc.)
        data: fields to update
        files: files to attach (unused by the current endpoint)

    Returns:
        Updated object data dict, or None on error.
    """
    logger.info(f"update_object: api_server={api_server}, mtype={mtype}, data={data}")

    web = f"{api_server}/api/{mtype}s/{id}"
    r = session.patch(web, data=data, headers=headers)

    response = r.json()
    if r.status_code != 200:
        logger.error(
            f"update_object: api_server={web}, mtype={mtype}, response={response['detail']}"
        )
        return None

    logger.debug(
        f"update_object: {web}, {mtype.upper()} created: \n{json.dumps(response, indent=4)}"
    )

    return response


def update_associative_object(
    session: requests.Session,
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "magnet",
    dtype: str = "part",
    data: dict = {},
    files: dict = {},
) -> dict | None:
    """Update an associative (join-table) object via PATCH.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        id: parent object ID
        mtype: parent resource type (e.g. "magnet")
        dtype: related resource type (e.g. "part")
        data: fields to update on the join row
        files: files to attach (unused by the current endpoint)

    Returns:
        Updated join-row data dict, or None on error.
    """
    logger.info(
        f"update_associative_object: api_server={api_server}, mtype={mtype}, data={data}"
    )

    web = f"{api_server}/api/{mtype}s/{id}/{dtype}s"
    r = session.patch(web, data=data, headers=headers)

    response = r.json()
    if r.status_code != 200:
        logger.error(
            f"update_associative_object: api_server={web}, mtype={mtype}, response={response['detail']}"
        )
        return None

    logger.debug(
        f"update_associative_object: {web}, {mtype.upper()} created: \n{json.dumps(response, indent=4)}"
    )

    return response


def del_object(
    session: requests.Session,
    api_server: str,
    headers: dict,
    mtype: str = "magnet",
    id: int | None = None,
) -> dict | None:
    """Delete an object by ID.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        mtype: resource type (magnet, part, site, etc.)
        id: object ID to delete

    Returns:
        API response dict, or None on error.
    """
    logger.info(f"del_object: api_server={api_server}, mtype={mtype}, id={id}")
    r = session.delete(
        f"{api_server}/api/{mtype}s/{id}", data={"id": id}, headers=headers
    )
    response = r.json()
    if r.status_code != 200:
        logger.error(response["detail"])
        return None

    logger.info(f"{response}")
    return response


def add_data_to_object(
    session: requests.Session,
    api_server: str,
    headers: dict,
    id: int,
    data: dict,
    mtype: str = "magnet",
    dtype: str = "part",
) -> None:
    """Post form data to a nested resource endpoint (e.g. /api/magnets/{id}/parts).

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        id: parent object ID
        data: form data to post (e.g. {"part_id": 5})
        mtype: parent resource type (e.g. "magnet")
        dtype: nested resource type (e.g. "part")
    """
    logger.info(
        f"add_data_to_object: api_server={api_server}, mtype={mtype}, id={id}, dtype={dtype}, data={data}"
    )

    logger.info(f"add_data_to_object: {api_server}/api/{mtype}s/{id}/{dtype}s")
    r = session.post(
        f"{api_server}/api/{mtype}s/{id}/{dtype}s",
        data=data,
        headers=headers,
    )
    logger.debug(f"add_data_to_object: r={r}")
    response = r.json()
    logger.debug(f"add_data_to_object: response={response}")
    if r.status_code != 200:
        logger.error(response["detail"])
        return None
    pass


def add_files_to_object(
    session: requests.Session,
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "part",
    dtype: str = "geometrie",
    files: dict = {},
) -> None:
    """Upload files to a nested resource endpoint (e.g. /api/parts/{id}/geometries).

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        id: parent object ID
        mtype: parent resource type (e.g. "part")
        dtype: nested resource type (e.g. "geometrie")
        files: multipart file dict accepted by requests
    """
    logger.info(
        f"add_files_to_object: api_server={api_server}, mtype={mtype}, id={id}, dtype={dtype}, files={files}"
    )

    r = session.post(
        f"{api_server}/api/{mtype}s/{id}/{dtype}s",
        files=files,
        headers=headers,
    )
    response = r.json()
    if r.status_code != 200:
        logger.error(response["detail"])
        return None
    pass


def add_data_files_to_object(
    session: requests.Session,
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "part",
    dtype: str = "geometrie",
    data: dict = {},
    files: dict = {},
) -> None:
    """Post both form data and files to a nested resource endpoint.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        id: parent object ID
        mtype: parent resource type (e.g. "part")
        dtype: nested resource type (e.g. "geometrie")
        data: form data fields (e.g. {"type": "default"})
        files: multipart file dict accepted by requests
    """
    logger.info(
        f"add_data_files_to_object: api_server={api_server}, mtype={mtype}, id={id}, dtype={dtype}, files={files}"
    )

    r = session.post(
        f"{api_server}/api/{mtype}s/{id}/{dtype}s",
        data=data,
        files=files,
        headers=headers,
    )
    response = r.json()
    if r.status_code != 200:
        logger.error(response["detail"])
        return None
    pass


def get_history(
    session: requests.Session,
    api_server: str,
    headers: dict,
    id: int,
    mtype: str = "magnet",
    otype: str = "record",
) -> list | None:
    """Return the list of related objects (records or sites) attached to an object.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        id: parent object ID
        mtype: parent resource type (part, magnet, or site)
        otype: related object type — "record" or "site"

    Returns:
        List of related object dicts, empty list if mtype not supported,
        or None on HTTP error.
    """
    logger.info(
        f"get_history: api_server={api_server}, mtype={mtype}, otype={otype}, id={id}"
    )

    r = session.get(f"{api_server}/api/{mtype}s/{id}", headers=headers)
    response = r.json()
    if r.status_code != 200:
        logger.error(
            f"get_history: api_server={api_server}, mtype={mtype}, otype={otype}, id={id} response={response['detail']}"
        )
        return None

    if mtype in ["part", "magnet", "site"]:
        r = session.get(f"{api_server}/api/{mtype}s/{id}/{otype}s", headers=headers)
        response = r.json()
        if r.status_code != 200:
            logger.error(
                f"get_history: {api_server}/api/{mtype}s/{id}/{otype}s response={response['detail']}"
            )
            return None
        return response[f"{otype}s"]

    return []


def get_data(
    session: requests.Session,
    api_server: str,
    headers: dict,
    oid: int,
    mtype: str = "magnet",
) -> dict | None:
    """Return the mdata payload attached to an object.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        oid: object ID
        mtype: resource type (magnet, part, etc.)

    Returns:
        mdata dict, or None on HTTP error.
    """
    logger.info(f"get_data: api_server={api_server}, mtype={mtype}, id={oid}")

    r = session.get(f"{api_server}/api/{mtype}s/{oid}/mdata", headers=headers)
    response = r.json()
    if r.status_code != 200:
        logger.error(
            f"get_data: api_server={api_server}/api/{mtype}s/{oid}/mdata, mtype={mtype}, id={oid} response={response['detail']}"
        )
        return None

    logger.debug(f"get_data: response={response}")
    return response


def post_data(
    session: requests.Session,
    api_server: str,
    headers: dict,
    data: dict,
    mtype: str = "magnet",
) -> dict | None:
    """Create an object by POSTing form data.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        data: form data dict
        mtype: resource type to create (magnet, part, site, etc.)

    Returns:
        Created object data dict, or None on HTTP error.
    """
    logger.info(f"post_data: api_server={api_server}, mtype={mtype}, data={data}")

    r = session.post(f"{api_server}/api/{mtype}s", data=data, headers=headers)
    response = r.json()
    if r.status_code != 200:
        logger.error(
            f"post_data: api_server={api_server}/api/{mtype}s, mtype={mtype}, response={response['detail']}"
        )
        return None

    logger.debug(f"post_data: response={response}")
    return response


def post_json(
    session: requests.Session,
    api_server: str,
    headers: dict,
    data: dict,
    mtype: str = "magnet",
) -> dict:
    """Create an object by POSTing a JSON body.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        data: JSON-serialisable dict
        mtype: resource type to create (material, record, simulation, etc.)

    Returns:
        Created object data dict.

    Raises:
        AuthenticationError: HTTP 401
        AuthorizationError: HTTP 403
        ResourceConflictError: HTTP 409
        ServerError: HTTP 5xx
        MagnetAPIException: any other non-200 response
    """
    logger.info(f"post_json: api_server={api_server}, mtype={mtype}, data={data}")

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

    logger.debug(f"post_json: response={response}")
    return response


def post_file(
    session: requests.Session,
    api_server: str,
    headers: dict,
    data: dict,
    mtype: str = "magnet",
) -> dict:
    """Upload a file by POSTing multipart form data.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        data: multipart file dict accepted by requests (e.g. {"file": <file object>})
        mtype: resource type (typically "attachment")

    Returns:
        Created object data dict (contains "id" of the new attachment).

    Raises:
        AuthenticationError: HTTP 401
        AuthorizationError: HTTP 403
        ServerError: HTTP 5xx
        MagnetAPIException: any other non-200 response
    """
    logger.info(f"post_file: api_server={api_server}, mtype={mtype}, files={data}")

    r = session.post(f"{api_server}/api/{mtype}s", files=data, headers=headers)
    response = r.json()
    logger.debug(f"post_file: response={response}")
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

    return response


def download(
    session: requests.Session,
    api_server: str,
    headers: dict,
    attach: str,
    wd: str = "",
) -> str | None:
    """Download an attachment by ID and write it to disk.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        attach: attachment ID (as string)
        wd: working directory to write the file into (uses cwd if empty)

    Returns:
        Filename of the downloaded file, or None if the download failed.
    """
    import os

    logger.info(f"download: api_server={api_server}, attach={attach}")

    r = session.get(f"{api_server}/api/attachments/{attach}/download", headers=headers)
    if r.status_code != 200:
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
    headers: dict,
    attach: str,
) -> None:
    """Upload a file (stub — not yet implemented).

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        attach: local file path to upload
    """
    logger.info(f"upload: api_server={api_server}, attach={attach}")
    pass
