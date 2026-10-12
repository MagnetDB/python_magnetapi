# Part API Updates - python_magnetapi

## Summary

Updated `python_magnetapi` to be consistent with the latest magnetdb API changes for part geometry handling.

## Changes Made

### 1. `python_magnetapi/part.py`

#### Enhanced `create()` function:
- **Added support for new geometry parameters:**
  - `geometry_yaml_config`: Inline YAML string for geometry configuration
  - `geometry`: File path to YAML geometry configuration (converted to inline)
  - `geometry_shape`: Path to shape CSV file (for helix type parts)
  - `geometry_modelaxi`: Path to modelaxi JSON file (for helix/bitter type parts)

- **Improved metadata handling:**
  - Now properly serializes metadata dict to JSON string
  - Defaults to "{}" if not provided

- **Two-step creation process:**
  1. POST to create part with basic fields (name, type, material_id, etc.)
  2. PATCH to update with geometry files (if provided)
  
  This is necessary because POST `/api/parts` doesn't support file uploads, only PATCH `/api/parts/{id}` does.

#### Added new `update()` function:
- Complete implementation for updating existing parts
- Supports all geometry-related fields:
  - `geometry_yaml_config`: Inline YAML
  - `geometry`: YAML file path (auto-converted to inline)
  - `geometry_shape`: Shape CSV file
  - `geometry_modelaxi`: ModelAxi JSON file
- Handles material updates (by name or dict)
- Properly manages file handles (opens and closes)
- Uses PATCH endpoint with multipart/form-data for file uploads

### 2. `python_magnetapi/utils.py`

#### Fixed `update_object()` function:
- **Bug fix:** Function accepted `files` parameter but didn't use it
- Now properly sends files in PATCH request when provided
- Uses `session.patch(web, data=data, files=files, headers=headers)` when files are present
- Improved error handling and debug messages
- Updated docstring with comprehensive parameter documentation

## Usage Examples

### Creating a Part with Geometry

```python
import python_magnetapi as api

# Basic part creation with inline geometry YAML
data = {
    "name": "MyHelix",
    "type": "helix",
    "description": "Test helix part",
    "material": "CuCrZr",
    "geometry_yaml_config": """---
!Helix
name: MyHelix
r: [19.3, 24.2]
z: []
cutwidth: 0.2
odd: true
dble: true
modelaxi: !ModelAxi
  name: MyHelix
  h: 0.0
  turns: []
  pitch: []
model3d: !Model3D
  cad: MyHelix
shape: !Shape
  name: ''
  file: ''
""",
    "geometry_shape": "/path/to/shape.csv",
    "geometry_modelaxi": "/path/to/modelaxi.json"
}

part_id = api.part.create(session, api_server, headers, data)
```

### Creating Part with Geometry File

```python
# Using geometry file (will be read and sent as inline YAML)
data = {
    "name": "MyHelix",
    "type": "helix",
    "material": "CuCrZr",
    "geometry": "/path/to/geometry.yaml",  # Will be read and sent inline
    "geometry_shape": "/path/to/shape.csv",
    "geometry_modelaxi": "/path/to/modelaxi.json"
}

part_id = api.part.create(session, api_server, headers, data)
```

### Updating a Part

```python
# Update existing part with new geometry
update_data = {
    "description": "Updated description",
    "geometry_yaml_config": "...",  # New inline YAML
    "geometry_shape": "/path/to/new_shape.csv"
}

result = api.part.update(session, api_server, headers, part_id, update_data)
```

## Important Notes

### Geometry YAML File References

⚠️ **Critical:** When providing `geometry_yaml_config` (inline YAML), it should be **fully expanded** without file references.

❌ **Don't do this:**
```yaml
!Helix
modelaxi: "modelaxi_file"  # File reference - will fail!
shape: "shape_file"        # File reference - will fail!
```

✅ **Do this instead:**
```yaml
!Helix
modelaxi: !ModelAxi
  name: MyHelix
  h: 0.0
  turns: []
  pitch: []
shape: !Shape
  name: ''
  file: ''
```

### File Constraints

- **geometry_shape**: Only allowed for `helix` type parts
- **geometry_modelaxi**: Only allowed for `helix` and `bitter` type parts
- All file paths must exist or a warning will be printed

### Backward Compatibility

The old usage patterns are still supported for basic part creation, but the new geometry handling is more robust and aligned with the magnetdb API.

## Testing

Test the changes with:

```bash
cd python_magnetapi
python -m pytest tests/test_part.py -v
```

(Note: Tests may need to be updated to cover new functionality)
