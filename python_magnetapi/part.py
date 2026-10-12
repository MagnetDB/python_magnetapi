"""
create part
"""

import json
import os

import requests

from . import material, utils
from .exceptions import ResourceConflictError, ResourceNotFoundError, ValidationError


def _load_geometry_yaml(geometry_file: str) -> str | None:
    """Load a geometry YAML file with python_magnetgeo and serialize it back.

    This validates the geometry and uses the object's to_yaml() method.

    Returns:
        YAML string, or None if the file could not be loaded.
    """
    # Lazy import: python_magnetgeo is only needed when uploading geometries
    import python_magnetgeo as pmg

    try:
        # Register YAML constructors before loading (required for lazy loading)
        pmg.verify_class_registration()
        geometry_obj = pmg.load(geometry_file)
        return geometry_obj.to_yaml()
    except pmg.ObjectLoadError as e:
        print(f"Failed to load geometry from {geometry_file}: {e}")
    except pmg.UnsupportedTypeError as e:
        print(f"Invalid geometry type in {geometry_file}: {e}")
    return None


def create(
    session: requests.Session,
    api_server: str,
    headers: dict,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
) -> int | None:
    """Create a part from a data dictionary.

    The "material" field may be a string (name lookup), a dict with an "id"
    (API response object used directly), or a dict without "id" (create-or-lookup
    by name).  Geometry and associated magnets are linked after creation.

    Args:
        session: requests session
        api_server: API server base URL
        headers: HTTP request headers
        data: dict with following keys:
            - name: part name (required)
            - type: part type (helix, ring, supra, etc.) (required)
            - description: part description (optional)
            - design_office_reference: reference (optional)
            - material: material name (str) or material dict (required)
            - metadata: dict of metadata (optional, default: {})
            - magnets: list of magnet names to associate (optional)

            Geometry configuration (choose ONE of these two options):
            - geometry: str - path to YAML file (e.g., "/data/geometries/HL-37_H1.yaml")
                       ⚠️ IMPORTANT: The YAML file MUST be fully expanded with NO file references.
                       File references like modelaxi: "filename" or shape: "filename" will FAIL.
                       The file will be read and its content sent to the API.
                       This is a CONVENIENCE parameter - use this if you have a file.
            - geometry_yaml_config: str - YAML content as a string (inline)
                       ⚠️ IMPORTANT: Must be fully expanded YAML with NO file references.
                       Use this if you already have the YAML content in memory.
                       This is what actually gets sent to the API.

            Additional geometry files (actual files to upload):
            - geometry_shape: str - path to shape DAT file (optional, only for helix type)
                             Example: "/data/shape/HL-37_H1.shape"
                             Format: Tab-separated text file with profile coordinates
            - geometry_modelaxi: str - path to modelaxi cut data file (optional, for helix/bitter)
                                Example: "/data/modelaxi/HL-37_H1.d"
                                Format: Tab-separated text file with theta, shape_id, z coordinates
        verbose: enable verbose output
        debug: enable debug output

    Returns:
        ID of the newly created part, or None if creation failed.

    Raises:
        ResourceConflictError: if a part with the same name already exists.
        ResourceNotFoundError: if the referenced material name is not found.
        ValidationError: if the "material" field type is invalid.

    Example:
        # Option 1: Using geometry file path (file will be read automatically)
        # NOTE: The YAML file MUST NOT contain file references!
        data = {
            "name": "H1",
            "type": "helix",
            "material": "CuCrZr",
            "geometry": "/data/geometries/HL-37_H1.yaml",  # File path - convenience
            "geometry_shape": "/data/shape/HL-37_H1.shape",
            "geometry_modelaxi": "/data/modelaxi/HL-37_H1.d"
        }
        # The YAML file must contain fully expanded objects like:
        # !<Helix>
        # modelaxi: !<ModelAxi>    ← Inline object, NOT "filename"
        #   name: H1
        #   h: 0.0
        # shape: !<Shape>          ← Inline object, NOT "filename"
        #   name: ''

        # Option 2: Using inline YAML (no file reading needed)
        data = {
            "name": "H1",
            "type": "helix",
            "material": "CuCrZr",
            "geometry_yaml_config": "!<Helix>\\nname: H1\\n...",  # Inline YAML string
            "geometry_shape": "/data/shape/HL-37_H1.shape",   # DAT format
            "geometry_modelaxi": "/data/modelaxi/HL-37_H1.d"  # Cut data format
        }
    """

    ids = utils.get_list(
        session, api_server, headers=headers, mtype="part"
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
        session, api_server, headers=headers, mtype="material"
    )
    mat = data["material"]
    if isinstance(mat, str):
        if mat in mat_ids:
            data["material_id"] = mat_ids[mat]
            del data["material"]
        else:
            raise ResourceNotFoundError(
                f"Material '{mat}' not found. "
                f"Create the material before creating part '{data['name']}'",
                object_name=mat,
                object_type="material",
                required_by=data["name"],
            )
    elif isinstance(mat, dict):
        # If the dict already has an "id" key it is an API response object —
        # use the id directly without an extra lookup.
        if "id" in mat:
            data["material_id"] = mat["id"]
        else:
            mname = mat["name"]
            _id = -1
            if mname in mat_ids:
                _id = mat_ids[mname]
            else:
                _id = material.create(
                    session, api_server, headers, mat
                )
            data["material_id"] = _id
        del data["material"]
    else:
        raise ValidationError(
            f"Invalid material type for part '{data['name']}'. "
            f"Expected string or dict, got {type(mat).__name__}",
            field="material",
            value_type=type(mat).__name__,
            expected_types=["str", "dict"],
        )

    # extract magnets list
    magnets = []
    if "magnets" in data:
        magnets = data["magnets"].copy()
        del data["magnets"]

    # Extract geometry-related fields
    geometry_file = data.pop("geometry", None)
    geometry_yaml_inline = data.pop("geometry_yaml_config", None)
    geometry_shape_file = data.pop("geometry_shape", None)
    geometry_modelaxi_file = data.pop("geometry_modelaxi", None)

    # Remove status if present (will be set to 'in_study' by default)
    data.pop("status", None)

    # Prepare form data for POST request
    form_data = {
        "name": data["name"],
        "type": data["type"],
        "material_id": data["material_id"],
    }

    # Add optional fields
    if "description" in data:
        form_data["description"] = data["description"]
    if "design_office_reference" in data:
        form_data["design_office_reference"] = data["design_office_reference"]
    if "metadata" in data:
        form_data["metadata"] = json.dumps(data["metadata"])
    else:
        form_data["metadata"] = "{}"

    print(f"part/create: form_data={form_data}")
    response = utils.post_data(
        session, api_server, headers, form_data, "part"
    )
    if response is None:
        print(f"part {data['name']} failed to be created")
        return None
    print(f"part {data['name']} created with id={response['id']}")
    part_id = response["id"]

    # Now update with geometry if provided
    # Note: Geometry should be provided via PATCH after part creation
    # because POST doesn't support file uploads for geometry
    if (
        geometry_file
        or geometry_yaml_inline
        or geometry_shape_file
        or geometry_modelaxi_file
    ):
        update_data = {
            "name": data["name"],
            "type": data["type"],
            "material_id": data["material_id"],
        }
        if "description" in data:
            update_data["description"] = data["description"]
        if "design_office_reference" in data:
            update_data["design_office_reference"] = data["design_office_reference"]

        # Prepare files dict for update
        files = {}

        # Handle geometry YAML config
        if geometry_yaml_inline:
            # Inline YAML string provided
            update_data["geometry_yaml_config"] = geometry_yaml_inline
        elif geometry_file:
            # YAML file path provided - load as python_magnetgeo object, then serialize
            if os.path.isfile(geometry_file):
                geometry_yaml = _load_geometry_yaml(geometry_file)
                if geometry_yaml is None:
                    return None
                update_data["geometry_yaml_config"] = geometry_yaml
            else:
                print(f"Warning: geometry file {geometry_file} not found")

        # Handle shape file (CSV, only for helix)
        if geometry_shape_file and os.path.isfile(geometry_shape_file):
            files["geometry_shape"] = open(geometry_shape_file, "rb")
        elif geometry_shape_file:
            print(f"Warning: geometry_shape file {geometry_shape_file} not found")

        # Handle modelaxi file (JSON, for helix/bitter)
        if geometry_modelaxi_file and os.path.isfile(geometry_modelaxi_file):
            files["geometry_modelaxi"] = open(geometry_modelaxi_file, "rb")
        elif geometry_modelaxi_file:
            print(
                f"Warning: geometry_modelaxi file {geometry_modelaxi_file} not found"
            )

        # Update part with geometry
        if update_data.get("geometry_yaml_config") or files:
            update_response = utils.update_object(
                session,
                api_server,
                headers,
                part_id,
                mtype="part",
                data=update_data,
                files=files,
            )

            # Close file handles
            for f in files.values():
                f.close()

            if update_response is None:
                print(
                    f"Warning: failed to update part {data['name']} with geometry"
                )
            else:
                print(f"part {data['name']} updated with geometry")

    # add magnets to part
    for magnet in magnets:
        _ids = utils.get_list(
            session, api_server, headers=headers, mtype="magnet"
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
            )
        else:
            print(
                f"part {data['name']} failed to be created MagnetPart: no magnet {magnet}"
            )

    # add cad, ...
    # see also status in python_magnetdb/models/status.py
    # how to change timestamps

    return part_id


def update(
    session: requests.Session,
    api_server: str,
    headers: dict,
    part_id: int,
    data: dict,
    verbose: bool = False,
    debug: bool = False,
) -> dict | None:
    """
    Update an existing part.

    Args:
        session: requests session
        api_server: API server URL
        headers: HTTP headers including Authorization
        part_id: ID of part to update
        data: dict with fields to update:
            - name: part name (optional)
            - type: part type (optional)
            - description: part description (optional)
            - design_office_reference: reference (optional)
            - material: material name (str) or material dict (optional)
            - metadata: dict of metadata (optional)

            Geometry configuration (choose ONE of these two options):
            - geometry: str - path to YAML file
                       ⚠️ IMPORTANT: The YAML file MUST be fully expanded with NO file references.
                       The file will be read and its content sent to the API.
            - geometry_yaml_config: str - YAML content as a string (inline)
                       ⚠️ IMPORTANT: Must be fully expanded YAML with NO file references.
                       This is what actually gets sent to the API.

            Additional geometry files (actual files to upload):
            - geometry_shape: str - path to shape DAT file (optional)
                             Format: Tab-separated text file with profile data
            - geometry_modelaxi: str - path to modelaxi cut data file (optional)
                                Format: Tab-separated text file (theta, shape_id, z)
        verbose: enable verbose output
        debug: enable debug output

    Returns:
        updated part data if successful, None otherwise
    """

    # Get current part to fill in any missing required fields
    current_part = utils.get_object(
        session,
        api_server,
        headers,
        part_id,
        mtype="part",
    )
    if current_part is None:
        print(f"part/update: part with id={part_id} not found")
        return None

    # Prepare update data
    update_data = {
        "name": data.get("name", current_part["name"]),
        "type": data.get("type", current_part["type"]),
        "material_id": str(
            current_part["material"]["id"]
        ),  # Always use current material_id
    }

    # Handle material update if provided
    if "material" in data:
        mat = data["material"]
        mat_ids = utils.get_list(
            session, api_server, headers=headers, mtype="material"
        )
        if isinstance(mat, str):
            if mat in mat_ids:
                update_data["material_id"] = str(mat_ids[mat])
            else:
                print(f"part/update: material {mat} not found")
                return None
        elif isinstance(mat, dict):
            mname = mat["name"]
            if mname in mat_ids:
                update_data["material_id"] = str(mat_ids[mname])
            else:
                # Create new material
                _id = material.create(
                    session, api_server, headers, mat, verbose=verbose, debug=debug
                )
                update_data["material_id"] = str(_id)

    # Add optional fields if provided
    if "description" in data:
        update_data["description"] = data["description"]
    if "design_office_reference" in data:
        update_data["design_office_reference"] = data["design_office_reference"]
    if "metadata" in data:
        update_data["metadata"] = json.dumps(data["metadata"])

    # Handle geometry files
    files = {}
    geometry_file = data.get("geometry")
    geometry_yaml_inline = data.get("geometry_yaml_config")
    geometry_shape_file = data.get("geometry_shape")
    geometry_modelaxi_file = data.get("geometry_modelaxi")

    # Handle geometry YAML config
    if geometry_yaml_inline:
        update_data["geometry_yaml_config"] = geometry_yaml_inline
    elif geometry_file:
        if os.path.isfile(geometry_file):
            with open(geometry_file) as f:
                update_data["geometry_yaml_config"] = f.read()
        else:
            print(f"Warning: geometry file {geometry_file} not found")

    # Handle shape file (CSV, only for helix)
    if geometry_shape_file and os.path.isfile(geometry_shape_file):
        files["geometry_shape"] = open(geometry_shape_file, "rb")
    elif geometry_shape_file:
        print(f"Warning: geometry_shape file {geometry_shape_file} not found")

    # Handle modelaxi file (JSON, for helix/bitter)
    if geometry_modelaxi_file and os.path.isfile(geometry_modelaxi_file):
        files["geometry_modelaxi"] = open(geometry_modelaxi_file, "rb")
    elif geometry_modelaxi_file:
        print(f"Warning: geometry_modelaxi file {geometry_modelaxi_file} not found")

    if verbose:
        print(f"part/update: updating part {part_id} with data={update_data}")

    # Update the part
    response = utils.update_object(
        session,
        api_server,
        headers,
        part_id,
        mtype="part",
        data=update_data,
        files=files,
    )

    # Close file handles
    for f in files.values():
        f.close()

    if response is None:
        print(f"part/update: failed to update part {part_id}")
        return None

    print(f"part/update: part {part_id} updated successfully")
    return response
