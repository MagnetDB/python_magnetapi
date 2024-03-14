"""
create attachment
"""

import os
from . import utils


def create(
    session,
    api_server: str,
    headers: dict,
    data: str,
    verbose: bool = False,
    debug: bool = False,
):
    """
    create an attachment from a data dictionnary
    """
    print(f"attachment/create: data={data}")

    (basedir, basename) = os.path.split(data)
    cwd = os.getcwd()
    if basedir:
        os.chdir(basedir)

    files = {"file": open(basename, "rb")}

    # create an attachment
    response = utils.post_file(
        session, api_server, headers, files, "attachment", verbose, debug
    )
    if response is None:
        print(f"{data['name']} failed to create attachment {data}")
        return None
    os.chdir(cwd)
    print(f"attachment/create: response={response}")

    return response["id"]
