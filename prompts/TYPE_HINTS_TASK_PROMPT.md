# Type Hints and Static Analysis Setup

## Task Overview

**Priority**: Tier 1 (High Impact, Foundation) - Partial  
**Status**: Minimal type hints exist  
**Estimated Effort**: Large (affects all ~15 Python modules)  
**Breaking Changes**: No (type hints are optional at runtime)  

## Current State Analysis

### What Exists ✓
- ✅ Basic type hints in some function signatures (`api_server: str`, `verbose: bool`, etc.)
- ✅ Minimal typing imports in `hoop_stress.py` and `hoop_stress_parallel.py` (`from typing import Sequence`)
- ✅ Python 3.11+ support (modern type hint syntax available)

### What's Missing ❌
- ❌ **No return type annotations** on most functions
- ❌ **No py.typed marker** - Package not recognized as typed by type checkers
- ❌ **No mypy configuration** - No static type checking setup
- ❌ **Inconsistent type hints** - Some functions have partial hints, others have none
- ❌ **No complex type annotations** - No Union, Optional, List, Dict annotations
- ❌ **No TypedDict** for structured data (API responses, configuration)
- ❌ **No Protocol definitions** for duck-typed interfaces
- ❌ **No type narrowing** with isinstance checks
- ❌ **No integration in CI/CD** - Type checking not automated

### Files Requiring Updates

**All modules need type hints:**
- `python_magnetapi/utils.py` - API utility functions (~15 functions)
- `python_magnetapi/cli.py` - CLI functions (~900 lines, many functions)
- `python_magnetapi/part.py` - Part operations (~10 functions)
- `python_magnetapi/magnet.py` - Magnet operations (~10 functions)
- `python_magnetapi/site.py` - Site operations (~8 functions)
- `python_magnetapi/record.py` - Record operations (~8 functions)
- `python_magnetapi/material.py` - Material operations (~8 functions)
- `python_magnetapi/geometry.py` - Geometry operations (~5 functions)
- `python_magnetapi/attachment.py` - Attachment operations (~5 functions)
- `python_magnetapi/flow_params.py` - Flow computations (~10 functions)
- `python_magnetapi/hoop_stress.py` - Hoop stress computations (~12 functions)
- `python_magnetapi/hoop_stress_parallel.py` - Parallel computations (~10 functions)
- `python_magnetapi/inductances.py` - Inductance computations (~5 functions)
- `python_magnetapi/__init__.py` - Package exports

---

## Implementation Plan

### Phase 1: Foundation and Configuration

#### Step 1.1: Create py.typed Marker

Create empty `python_magnetapi/py.typed` file to indicate package supports type hints:

```bash
touch python_magnetapi/py.typed
```

This signals to type checkers that the package provides type information (PEP 561).

**Update pyproject.toml** to include py.typed in package data:

```toml
[tool.setuptools.package-data]
python_magnetapi = ["py.typed"]
```

#### Step 1.2: Configure mypy

Add mypy configuration to `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Start lenient, tighten later
disallow_incomplete_defs = false
check_untyped_defs = true
disallow_untyped_calls = false
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
show_error_codes = true
show_column_numbers = true
pretty = true

# Gradually increase strictness
[[tool.mypy.overrides]]
module = "python_magnetapi.utils"
disallow_untyped_defs = true  # Enforce for completed modules

[[tool.mypy.overrides]]
module = "python_magnetapi.exceptions"
disallow_untyped_defs = true

# Third-party libraries without stubs
[[tool.mypy.overrides]]
module = [
    "python_magnetsetup.*",
    "python_magnetcooling.*",
    "python_magnettools.*",
    "python_magnetrun.*",
    "magnettools.*",
    "param.*",
]
ignore_missing_imports = true
```

#### Step 1.3: Add mypy to dev dependencies

Update `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-cov",
    "mypy>=1.8.0",
    "types-requests",  # Type stubs for requests
]
```

#### Step 1.4: Create Type Aliases File

Create `python_magnetapi/types.py` for common type aliases:

```python
"""Type aliases and TypedDict definitions for python-magnetapi."""

from typing import TypedDict, Union, Optional, Dict, Any, List
import requests

# Type aliases
SessionType = requests.Session
HeadersDict = Dict[str, str]
JSONDict = Dict[str, Any]

# API Response types (based on actual API structure)
class PagedResponse(TypedDict):
    """Structure of paginated API responses."""
    current_page: int
    last_page: int
    items: List[JSONDict]
    total: int


class MaterialData(TypedDict, total=False):
    """Material data structure (total=False means all fields optional)."""
    name: str
    id: int
    nuance: Optional[str]
    type: str
    properties: Dict[str, Any]


class PartData(TypedDict, total=False):
    """Part data structure."""
    name: str
    id: int
    material_id: int
    type: str
    status: Optional[str]
    geometry: Optional[List[int]]


class MagnetData(TypedDict, total=False):
    """Magnet data structure."""
    name: str
    id: int
    be: str
    parts: List[int]


class SiteData(TypedDict, total=False):
    """Site data structure."""
    name: str
    id: int
    magnets: List[int]
    records: List[int]


class RecordData(TypedDict, total=False):
    """Record data structure."""
    name: str
    id: int
    date: str
    data: Dict[str, Any]


class SimulationData(TypedDict, total=False):
    """Simulation data structure."""
    name: str
    id: int
    resource_type: str
    resource_id: int
    method: str
    geometry: str
    model: str
    cooling: str


# Type for resource types
ResourceType = Union[
    "material", "part", "magnet", "site", "record", "simulation", "attachment"
]

# ID type
ResourceID = int
```

---

### Phase 2: Add Type Hints to Core Modules

#### Step 2.1: Type Hints for utils.py (High Priority)

This is the most critical module - all API interactions go through it.

**Pattern for get_list():**
```python
from typing import Dict, Optional
from .types import SessionType, HeadersDict, ResourceType

def get_list(
    session: SessionType,
    api_server: str,
    headers: HeadersDict,
    mtype: ResourceType = "magnets",
    verbose: bool = False,
    debug: bool = False,
) -> Dict[str, int]:
    """
    Return list of ids for selected type.
    
    Args:
        session: Requests session object
        api_server: Base URL of MagnetDB API
        headers: HTTP headers for authentication
        mtype: Resource type to list
        verbose: Enable verbose output
        debug: Enable debug output
        
    Returns:
        Dictionary mapping resource names to their IDs
        
    Raises:
        APIError: If API request fails
        AuthenticationError: If authentication fails
    """
    # ... implementation ...
```

**Pattern for get_object():**
```python
from typing import Optional
from .types import SessionType, HeadersDict, ResourceType, ResourceID, JSONDict

def get_object(
    session: SessionType,
    api_server: str,
    headers: HeadersDict,
    id: ResourceID,
    mtype: ResourceType = "magnet",
    verbose: bool = False,
    debug: bool = False,
) -> Optional[JSONDict]:
    """
    Return object data by ID.
    
    Args:
        session: Requests session object
        api_server: Base URL of MagnetDB API
        headers: HTTP headers for authentication
        id: Resource ID to retrieve
        mtype: Resource type
        verbose: Enable verbose output
        debug: Enable debug output
        
    Returns:
        Resource data dictionary, or None if not found
        
    Raises:
        NotFoundError: If resource doesn't exist
        APIError: If API request fails
    """
    # ... implementation ...
```

**Pattern for create_object():**
```python
from typing import Dict, Any, Optional

def create_object(
    session: SessionType,
    api_server: str,
    headers: HeadersDict,
    mtype: ResourceType = "magnet",
    data: Dict[str, Any] = {},
    verbose: bool = False,
    debug: bool = False,
) -> ResourceID:
    """
    Create an object and return its ID.
    
    Args:
        session: Requests session object
        api_server: Base URL of MagnetDB API
        headers: HTTP headers for authentication
        mtype: Resource type to create
        data: Resource data
        verbose: Enable verbose output
        debug: Enable debug output
        
    Returns:
        ID of created resource
        
    Raises:
        ResourceCreationError: If creation fails
        ValidationError: If data is invalid
        APIError: If API request fails
    """
    # ... implementation ...
```

**Apply same pattern to all utils.py functions:**
- `update_object()` → returns `ResourceID`
- `del_object()` → returns `None`
- `add_data_to_object()` → returns `bool`
- `get_data()` → returns `Optional[JSONDict]`
- `post_data()` → returns `ResourceID`
- etc.

#### Step 2.2: Type Hints for Domain Modules

**Pattern for part.py create():**
```python
from typing import Dict, Any, List, Optional, Union
from .types import SessionType, HeadersDict, ResourceID, PartData

def create(
    session: SessionType,
    api_server: str,
    headers: HeadersDict,
    data: PartData,
    verbose: bool = False,
    debug: bool = False,
) -> ResourceID:
    """
    Create a part in MagnetDB.
    
    Args:
        session: Requests session object
        api_server: Base URL of MagnetDB API
        headers: HTTP headers for authentication
        data: Part data including name, material, type, etc.
        verbose: Enable verbose output
        debug: Enable debug output
        
    Returns:
        ID of created part
        
    Raises:
        InvalidDataError: If part data is invalid
        ResourceCreationError: If creation fails
    """
    # ... implementation ...
```

**Apply to all domain modules:**
- `magnet.py` - Use `MagnetData`
- `site.py` - Use `SiteData`
- `record.py` - Use `RecordData`
- `material.py` - Use `MaterialData`
- `geometry.py` - Add specific geometry types
- `attachment.py` - Add file-related types

#### Step 2.3: Type Hints for Computation Modules

**Pattern for hoop_stress.py:**
```python
from typing import Optional, Union, Dict, List, Tuple
import numpy as np
import pandas as pd
from numpy.typing import NDArray

# Type aliases for arrays
FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int32]

def compute_hoop_stress(
    geometry: Dict[str, Any],
    material_properties: Dict[str, float],
    current: Union[float, FloatArray],
    temperature: Optional[FloatArray] = None,
    verbose: bool = False,
) -> pd.DataFrame:
    """
    Compute hoop stress for given geometry and conditions.
    
    Args:
        geometry: Geometry definition with r, z coordinates
        material_properties: Material properties (E, nu, alpha, etc.)
        current: Current value(s) in Amperes
        temperature: Temperature distribution (optional)
        verbose: Enable verbose output
        
    Returns:
        DataFrame with hoop stress results
        
    Raises:
        InvalidParameterError: If parameters are invalid
        ComputationError: If computation fails
    """
    # ... implementation ...
```

**Apply to all computation modules:**
- `flow_params.py` - Add physics parameter types
- `inductances.py` - Add electrical parameter types
- `hoop_stress_parallel.py` - Reuse types from hoop_stress.py

#### Step 2.4: Type Hints for CLI Module

The CLI module is large (900+ lines) but type hints are still valuable:

```python
from typing import Optional, List
import argparse

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    # ... implementation ...
    return parser.parse_args()

def main(argv: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point.
    
    Args:
        argv: Command-line arguments (for testing)
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        args = parse_args()
        # ... implementation ...
        return 0
    except Exception as e:
        # ... error handling ...
        return 1
```

---

### Phase 3: Advanced Type Hints

#### Step 3.1: Add Protocol Definitions

For duck-typed interfaces, use Protocol (Python 3.8+):

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class GeometryProvider(Protocol):
    """Protocol for objects that provide geometry data."""
    
    def get_coordinates(self) -> Tuple[FloatArray, FloatArray]:
        """Return (r, z) coordinate arrays."""
        ...
    
    def get_volumes(self) -> FloatArray:
        """Return volume array."""
        ...

# Usage:
def compute_field(geometry: GeometryProvider) -> FloatArray:
    r, z = geometry.get_coordinates()
    # ... computation ...
```

#### Step 3.2: Add Generic Types

For reusable components:

```python
from typing import TypeVar, Generic, Callable

T = TypeVar('T')
R = TypeVar('R')

class APICache(Generic[T]):
    """Generic cache for API responses."""
    
    def get(self, key: str) -> Optional[T]:
        """Get cached value."""
        ...
    
    def set(self, key: str, value: T) -> None:
        """Set cached value."""
        ...

# Usage:
magnet_cache: APICache[MagnetData] = APICache()
```

#### Step 3.3: Add Type Narrowing

Use isinstance checks to narrow types:

```python
def process_material(material: Union[str, MaterialData, int]) -> MaterialData:
    """Process material specification."""
    if isinstance(material, str):
        # Type narrowed to str
        return fetch_material_by_name(material)
    elif isinstance(material, int):
        # Type narrowed to int
        return fetch_material_by_id(material)
    else:
        # Type narrowed to MaterialData
        return material
```

#### Step 3.4: Add Literal Types

For string enums:

```python
from typing import Literal

ResourceType = Literal[
    "material", "part", "magnet", "site", "record", "simulation", "attachment"
]

def get_resource(
    resource_type: ResourceType,
    resource_id: int
) -> JSONDict:
    """Get resource by type and ID."""
    # Type checker ensures only valid types are passed
    ...
```

---

### Phase 4: Integration and Validation

#### Step 4.1: Run mypy Locally

```bash
# Install mypy and type stubs
pip install mypy types-requests

# Run mypy on entire package
mypy python_magnetapi/

# Run mypy with strict mode on specific modules
mypy --strict python_magnetapi/utils.py

# Generate HTML report
mypy --html-report mypy-report python_magnetapi/
```

#### Step 4.2: Fix Type Errors Incrementally

**Common patterns and fixes:**

**1. Any type errors:**
```python
# Before:
def process_data(data):  # Implicit Any
    ...

# After:
def process_data(data: Dict[str, Any]) -> None:
    ...
```

**2. Optional return values:**
```python
# Before:
def find_item(name: str):
    # Sometimes returns None
    ...

# After:
def find_item(name: str) -> Optional[ItemData]:
    ...
```

**3. Union types:**
```python
# Before:
def handle_id(id):
    # Can be str or int
    ...

# After:
def handle_id(id: Union[str, int]) -> None:
    ...
```

**4. Missing return statements:**
```python
# Before:
def get_value() -> str:
    if condition:
        return "value"
    # mypy error: Missing return statement

# After:
def get_value() -> str:
    if condition:
        return "value"
    return "default"  # or raise exception
```

#### Step 4.3: Add Type Checking to CI/CD

Create `.github/workflows/type-check.yml`:

```yaml
name: Type Check

on: [push, pull_request]

jobs:
  mypy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      
      - name: Run mypy
        run: |
          mypy python_magnetapi/ --no-error-summary
      
      - name: Upload report
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: mypy-report
          path: mypy-report/
```

#### Step 4.4: Configure IDE Integration

**VS Code settings.json:**
```json
{
  "python.linting.mypyEnabled": true,
  "python.linting.mypyArgs": [
    "--config-file=pyproject.toml"
  ],
  "python.analysis.typeCheckingMode": "basic"
}
```

**PyCharm:**
- Enable mypy plugin from marketplace
- Configure External Tools → mypy with `--config-file pyproject.toml`

---

### Phase 5: Documentation and Best Practices

#### Step 5.1: Update Docstrings

Add type information to docstrings (NumPy/Google style):

```python
def create_magnet(
    session: SessionType,
    data: MagnetData,
    verbose: bool = False,
) -> ResourceID:
    """
    Create a magnet in MagnetDB.
    
    Parameters
    ----------
    session : requests.Session
        Active requests session with authentication
    data : MagnetData
        Magnet configuration including name, BE, parts list
    verbose : bool, default=False
        Enable verbose output
        
    Returns
    -------
    int
        ID of created magnet
        
    Raises
    ------
    InvalidDataError
        If magnet data is invalid or incomplete
    ResourceCreationError
        If creation fails on the server
    APIError
        If API request fails
        
    Examples
    --------
    >>> magnet_data = {"name": "M10", "be": "Bitter", "parts": [1, 2, 3]}
    >>> magnet_id = create_magnet(session, magnet_data)
    >>> print(f"Created magnet {magnet_id}")
    """
    # ... implementation ...
```

#### Step 5.2: Create Type Hints Documentation

Add `docs/type_hints.rst`:

```rst
Type Hints Guide
================

python-magnetapi is fully typed using Python type hints (PEP 484).

Type Stubs
----------

The package includes a ``py.typed`` marker, making it compatible with
type checkers like mypy, pyright, and Pyre.

Common Types
------------

The package defines common types in ``python_magnetapi.types``:

.. code-block:: python

    from python_magnetapi.types import (
        MagnetData,
        PartData,
        SiteData,
        ResourceID,
    )

Type Checking Your Code
-----------------------

To type-check code using python-magnetapi:

.. code-block:: bash

    pip install mypy types-requests
    mypy your_script.py

Using Type Hints
----------------

All public API functions include type hints:

.. code-block:: python

    from python_magnetapi import utils
    from python_magnetapi.types import SessionType, HeadersDict
    
    def my_function(session: SessionType, headers: HeadersDict) -> None:
        magnets = utils.get_list(session, "http://api", headers, "magnet")
        # Type checker knows magnets is Dict[str, int]
        for name, id in magnets.items():
            print(f"{name}: {id}")

Type Narrowing
--------------

Use isinstance() for type narrowing:

.. code-block:: python

    from typing import Union
    
    def process_input(value: Union[str, int, dict]) -> str:
        if isinstance(value, str):
            return value  # Type narrowed to str
        elif isinstance(value, int):
            return str(value)  # Type narrowed to int
        else:
            return value["name"]  # Type narrowed to dict
```

#### Step 5.3: Add Type Checking to Development Workflow

Update `README.md`:

```markdown
## Development

### Type Checking

This project uses type hints and mypy for static type checking:

```bash
# Run type checker
mypy python_magnetapi/

# Run type checker on specific module
mypy python_magnetapi/utils.py --strict

# Generate HTML report
mypy --html-report mypy-report python_magnetapi/
```

### Pre-commit Hooks

Install pre-commit hooks for automatic type checking:

```bash
pip install pre-commit
pre-commit install
```
```

#### Step 5.4: Create Type Hints Best Practices Guide

Add to `docs/contributing.rst`:

```rst
Type Hints Guidelines
---------------------

When adding new code:

1. **Always add type hints** to function signatures
2. **Use specific types** over ``Any`` when possible
3. **Document types** in docstrings
4. **Run mypy** before committing
5. **Add type stubs** for external libraries if needed

Examples:

Good:
    .. code-block:: python
    
        def fetch_data(id: int, timeout: float = 30.0) -> Optional[dict]:
            \"\"\"Fetch data by ID.\"\"\"
            ...

Bad:
    .. code-block:: python
    
        def fetch_data(id, timeout=30.0):  # No type hints
            ...
```

---

## Implementation Guidelines

### Incremental Approach

1. **Start with types.py** - Define all TypedDict classes first
2. **Complete utils.py** - Core module, type everything
3. **One domain module at a time** - part.py, then magnet.py, etc.
4. **Computation modules** - More complex types, numpy arrays
5. **CLI module last** - Large but straightforward
6. **Enable strict mode gradually** - Per module in mypy config

### Type Hint Priorities

**High Priority (Must Have):**
- Function parameters and return types
- Public API functions
- TypedDict for structured data

**Medium Priority (Should Have):**
- Class attributes
- Instance variables
- Local variables in complex functions

**Low Priority (Nice to Have):**
- Private functions (can use `# type: ignore` sparingly)
- Very dynamic code (use `Any` if necessary)

### Dealing with Untyped Dependencies

For dependencies without type stubs:

```toml
[[tool.mypy.overrides]]
module = "untyped_library.*"
ignore_missing_imports = true
```

Or create stub files in `stubs/` directory.

### Common Type Patterns

**Optional values:**
```python
from typing import Optional

def find_by_name(name: str) -> Optional[dict]:
    # Returns dict or None
    ...
```

**Union types:**
```python
from typing import Union

def process(value: Union[str, int, dict]) -> str:
    ...
```

**Lists and Dicts:**
```python
from typing import List, Dict

def get_names() -> List[str]:
    ...

def get_mapping() -> Dict[str, int]:
    ...
```

**Callbacks:**
```python
from typing import Callable

def apply(func: Callable[[int], str]) -> str:
    return func(42)
```

---

## Testing Type Hints

### Create Type Checker Tests

Create `tests/test_types.py`:

```python
"""Tests for type hints (these test the types, not runtime behavior)."""

from python_magnetapi import utils
from python_magnetapi.types import MagnetData, PartData

# Type checker tests (use mypy to validate)
def test_magnet_data_structure() -> None:
    """Test MagnetData structure."""
    magnet: MagnetData = {
        "name": "M10",
        "id": 1,
        "be": "Bitter",
        "parts": [1, 2, 3],
    }
    assert magnet["name"] == "M10"


def test_utils_get_list_types() -> None:
    """Test get_list type signature."""
    # This tests that the types are correct
    from unittest.mock import Mock
    session = Mock()
    headers = {"Authorization": "Bearer token"}
    
    # Type checker verifies these calls are valid
    result = utils.get_list(session, "http://api", headers, "magnet")
    reveal_type(result)  # Should be Dict[str, int]
```

### Use reveal_type for Debugging

```python
from typing import reveal_type

def test_function() -> None:
    result = some_function()
    reveal_type(result)  # mypy will print the inferred type
```

---

## Success Criteria

✅ **Implementation Complete When:**
1. All public functions have full type hints (parameters + return)
2. `py.typed` marker file exists and is included in package
3. mypy configuration in pyproject.toml
4. All modules pass mypy with `check_untyped_defs = true`
5. At least core modules (utils, exceptions) pass with `--strict`
6. TypedDict definitions for all structured data
7. Type checking integrated in CI/CD
8. Documentation includes type hints guide
9. IDE integration configured (VS Code, PyCharm)
10. Zero critical type errors in mypy output

✅ **Quality Metrics:**
- mypy success rate ≥ 95% (some `# type: ignore` acceptable)
- All public APIs fully typed
- Type coverage ≥ 80% (use mypy --html-report to track)
- Zero untyped function definitions in core modules
- Documentation includes type information

---

## Troubleshooting Common Issues

### Issue 1: Third-party Library Without Stubs

**Solution:** Add to mypy overrides:
```toml
[[tool.mypy.overrides]]
module = "problematic_library.*"
ignore_missing_imports = true
```

### Issue 2: Complex Type that mypy Can't Infer

**Solution:** Use explicit type cast:
```python
from typing import cast, Dict

data = get_complex_data()
typed_data = cast(Dict[str, Any], data)
```

### Issue 3: Dynamic Attribute Access

**Solution:** Use TypedDict or define `__getattr__`:
```python
def __getattr__(self, name: str) -> Any:
    ...
```

### Issue 4: Too Many Type Errors

**Solution:** Start with lenient config, tighten gradually:
```toml
[tool.mypy]
disallow_untyped_defs = false  # Initially
check_untyped_defs = true      # Check even untyped
```

---

## References

**PEP References:**
- PEP 484: Type Hints
- PEP 526: Syntax for Variable Annotations
- PEP 544: Protocols
- PEP 561: Distributing and Packaging Type Information
- PEP 585: Type Hinting Generics In Standard Collections (Python 3.9+)
- PEP 604: Union Type as `X | Y` (Python 3.10+)

**Tools:**
- mypy: http://mypy-lang.org/
- typing module docs: https://docs.python.org/3/library/typing.html
- mypy cheat sheet: https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html

**Related Files:**
- `python_magnetapi/types.py` (new)
- `python_magnetapi/py.typed` (new)
- `pyproject.toml` (update [tool.mypy])
- All `.py` files in python_magnetapi/
- `tests/test_types.py` (new)
- `docs/type_hints.rst` (new)

---

## Notes for Implementation

1. **Start small** - Complete one module end-to-end before moving to next
2. **Test frequently** - Run mypy after each function is typed
3. **Use reveal_type()** - Debug type inference issues
4. **Don't overuse Any** - Try to use specific types, but `Any` is better than no hints
5. **TypedDict is powerful** - Use for structured API responses
6. **Protocol for duck typing** - Better than structural subtyping
7. **Consider backwards compatibility** - Type hints don't break runtime (Python 3.7+)

## Gradual Typing Strategy

**Week 1:** Foundation
- Create types.py, py.typed, mypy config
- Type hints for utils.py
- Basic CI integration

**Week 2:** Domain modules
- Type hints for all domain modules
- TypedDict for all data structures  
- Documentation updates

**Week 3:** Computation & CLI
- Type hints for computation modules
- Type hints for CLI
- Comprehensive tests

**Week 4:** Polish & Strict mode
- Enable strict mode for core modules
- Fix all remaining type errors
- Complete documentation

## Document Version

**Version**: 1.0  
**Created**: 2026-03-12  
**Task**: Type Hints and Static Analysis Setup  
**Priority**: Tier 1 (High Impact, Foundation) - Partial  
**Status**: Ready for implementation  
**Dependencies**: Should be done after or in parallel with Error Handling Framework
