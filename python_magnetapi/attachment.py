"""
create attachment
"""

import os
import requests

from . import utils


def create(
    session: requests.Session,
    api_server: str,
    headers: dict,
    data: str,
    verbose: bool = False,
    debug: bool = False,
) -> int | None:
    """Upload a local file and create an attachment record.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        data: local file path to upload
        verbose: enable verbose output
        debug: enable debug output

    Returns:
        ID of the newly created attachment, or None if upload failed.
    """
    print(f"attachment/create: data={data}")

    (basedir, basename) = os.path.split(data)
    cwd = os.getcwd()
    if basedir:
        os.chdir(basedir)

    files = {"file": open(basename, "rb")}

    # create an attachment
    response = utils.post_file(
        session, api_server, headers, files, "attachment"
    )
    if response is None:
        print(f"{data['name']} failed to create attachment {data}")
        return None
    os.chdir(cwd)
    print(f"attachment/create: response={response}")

    return response["id"]
