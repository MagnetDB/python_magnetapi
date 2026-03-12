"""
create part
"""

from . import utils
from . import material
from .exceptions import ResourceConflictError, ResourceNotFoundError, ValidationError


def create(
    session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
):
    """
    create a part from a data dictionnary
    """

    ids = utils.get_list(
        session, api_server, headers=headers, mtype="part", debug=debug
    )
    if data["name"] in ids:
        raise ResourceConflictError(
            f"Part '{data['name']}' already exists",
            object_name=data["name"],
            object_type="part",
            existing_id=ids[data["name"]],
        )

    # search or create material in db
    mat_ids = utils.get_list(
        session, api_server, headers=headers, mtype="material", debug=debug
    )
    mat = data["material"]
    if isinstance(mat, str):
        if mat in mat_ids:
            data["material_id"] = mat_ids[mat]
            del data["material"]
        else:
            raise ResourceNotFoundError(
                f"Material '{mat}' not found. Create the material before creating part '{data['name']}'",
                object_name=mat,
                object_type="material",
                required_by=data["name"],
            )
    elif isinstance(mat, dict):
        mname = mat["name"]
        _id = -1
        if mname in mat_ids:
            _id = mat_ids[mname]
        else:
            _id = material.create(
                session, api_server, headers, mat, verbose=verbose, debug=debug
            )

        data["material_id"] = _id
        del data["material"]
    else:
        raise ValidationError(
            f"Invalid material type for part '{data['name']}'. Expected string or dict, got {type(mat).__name__}",
            field="material",
            value_type=type(mat).__name__,
            expected_types=["str", "dict"],
        )

    # extract magnets list
    magnets = []
    if "magnets" in data:
        magnets = data["magnets"].copy()
        del data["magnets"]

    geometries = []
    if "geometry" in data:
        geometries = data["geometry"].copy()
        del data["geometry"]

    status = ""
    if "status" in data:
        status = data["status"]
        del data["status"]

    # get material id, and set data accordingly
    print(f"part/create: data={data}")
    response = utils.post_data(
        session, api_server, headers, data, "part", verbose, debug
    )
    if response is None:
        print(f"part {data['name']} failed to be created")
        return None
    print(f"part {data['name']} created with id={response['id']}")

    # add magnets
    part_id = response["id"]
    for magnet in magnets:
        _ids = utils.get_list(
            session, api_server, headers=headers, mtype="magnet", debug=debug
        )
        if magnet in _ids:
            _id = _ids[magnet]
            # how to create MagnetPart: use /api/magnets/{magnet_id}/parts
            # create(magnet_id: int, user=Depends(get_user('create')), part_id: int = Form(...))
            utils.add_data_to_object(
                session,
                api_server,
                headers,
                _id,
                data={"part_id": part_id},
                mtype="magnet",
                dtype="part",
                verbose=verbose,
                debug=debug,
            )
        else:
            print(
                f"part {data['name']} failed to be created MagnetPart: no magnet {magnet}"
            )

    # TODO better to have a dict for this part
    # data['geometry'] = {'default':} with additionnal from part type
    # see valid_geometry_types in geometry.py
    # add geometry: see geometry.create
    # for geometry: files: {'attachment': }
    # for cad (/api/cad_attachments) : files:{'file': }
    if geometries:
        geomfile = f"{geometries[0]}.yaml"
        utils.add_data_files_to_object(
            session,
            api_server,
            headers,
            response["id"],
            "part",
            "geometrie",
            data={"type": "default"},
            files={"geometry": geomfile},
            verbose=verbose,
            debug=debug,
        )

    # add cad, ...
    # see also status in python_magnetdb/models/status.py
    # how to change timestamps

    return response["id"]
