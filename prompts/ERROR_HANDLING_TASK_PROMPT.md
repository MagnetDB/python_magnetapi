# Error Handling and Exception Framework Implementation

## Task Overview

**Priority**: Tier 1 (High Impact, Foundation)
**Status**: 🛠️ IN PROGRESS — Foundation complete, propagation remaining
**Estimated Effort**: Medium (hierarchy done; ~10-15 files still need updating)
**Breaking Changes**: Yes (functions returning `None` will raise exceptions)

## Current State Analysis

### What Exists ✅
- ✅ `exceptions.py` created (121 lines) with `MagnetAPIException` base class and subclasses
- ✅ CLI (`cli/` package) wired to catch `MagnetAPIException` and `AuthenticationError` with Rich output
- ✅ Basic exception context via `**context` kwargs (status_code, url, response, etc.)

### Problems Remaining ❌
1. ❌ **Domain modules not updated** - `utils.py`, `part.py`, `magnet.py`, `site.py`, `record.py` still use `RuntimeError` / `print()`-based errors
2. ❌ **Silent failures remain** - Some functions still return `None` on error instead of raising
3. ❌ **Print-based errors** - `utils.py` and domain modules still use `print()` for error output
4. ❌ **No error recovery** - No retry logic implemented
5. ❌ **No error handling tests** - No tests for exception paths

### Files Requiring Updates

**High Priority:**
- `python_magnetapi/utils.py` - Core API functions (~50+ print statements for errors)
- `python_magnetapi/cli.py` - CLI error handling (~20+ generic RuntimeError instances)
- New file: `python_magnetapi/exceptions.py` - Custom exception hierarchy

**Medium Priority:**
- `python_magnetapi/part.py` - Domain module error handling
- `python_magnetapi/magnet.py` - Domain module error handling
- `python_magnetapi/site.py` - Domain module error handling
- `python_magnetapi/record.py` - Domain module error handling
- `python_magnetapi/material.py` - Domain module error handling
- `python_magnetapi/geometry.py` - Domain module error handling

**Low Priority:**
- `python_magnetapi/hoop_stress.py` - Computation error handling
- `python_magnetapi/hoop_stress_parallel.py` - Computation error handling
- `python_magnetapi/flow_params.py` - Computation error handling
- `python_magnetapi/inductances.py` - Computation error handling

**Testing:**
- New file: `tests/test_exceptions.py` - Exception framework tests

---

## Implementation Plan

### Phase 1: Foundation (Essential)

#### Step 1.1: Create Exception Hierarchy

Create `python_magnetapi/exceptions.py` with comprehensive exception classes:

```python
"""
Custom exceptions for python-magnetapi.

This module defines a hierarchy of exceptions used throughout the package
to provide clear, structured error handling with context.
"""


class MagnetAPIException(Exception):
    """Base exception for all python-magnetapi errors.
    
    All custom exceptions in this package inherit from this base class,
    allowing users to catch any package-specific error.
    
    Attributes:
        message (str): Human-readable error message
        context (dict): Additional context information (status_code, url, etc.)
    """
    
    def __init__(self, message, **context):
        """Initialize exception with message and optional context.
        
        Args:
            message: Human-readable error description
            **context: Additional context (status_code, url, response, etc.)
        """
        super().__init__(message)
        self.message = message
        self.context = context
    
    def __str__(self):
        """Format exception with context for display."""
        if not self.context:
            return self.message
        ctx = ", ".join(f"{k}={v}" for k, v in self.context.items())
        return f"{self.message} ({ctx})"


# API-related exceptions
class APIError(MagnetAPIException):
    """Base exception for API communication errors."""
    pass


class AuthenticationError(APIError):
    """Raised when API authentication fails.
    
    Typical causes:
    - Invalid API key
    - Missing credentials
    - Expired token
    """
    pass


class NotFoundError(APIError):
    """Raised when requested resource is not found (HTTP 404).
    
    Context should include:
        - resource_type: Type of resource (magnet, part, etc.)
        - resource_id: ID that was not found
    """
    pass


class APIRequestError(APIError):
    """Raised when API request fails.
    
    Includes network errors, timeouts, connection issues.
    """
    pass


class APIResponseError(APIError):
    """Raised when API returns unexpected or invalid response.
    
    Context should include:
        - status_code: HTTP status code
        - response: Response body (if available)
    """
    pass


class ForbiddenError(APIError):
    """Raised when access to resource is forbidden (HTTP 403).
    
    User lacks permissions for the requested operation.
    """
    pass


# Data validation exceptions
class ValidationError(MagnetAPIException):
    """Base exception for data validation errors."""
    pass


class InvalidDataError(ValidationError):
    """Raised when input data is invalid or malformed.
    
    Context should include:
        - field: Name of invalid field
        - value: Invalid value provided
        - expected: Expected format/type
    """
    pass


class MissingFieldError(ValidationError):
    """Raised when required field is missing.
    
    Context should include:
        - field: Name of missing field
        - resource_type: Type of resource being created/updated
    """
    pass


# Resource operation exceptions
class ResourceError(MagnetAPIException):
    """Base exception for resource operation errors."""
    pass


class ResourceCreationError(ResourceError):
    """Raised when resource creation fails."""
    pass


class ResourceUpdateError(ResourceError):
    """Raised when resource update fails."""
    pass


class ResourceDeletionError(ResourceError):
    """Raised when resource deletion fails."""
    pass


# Computation exceptions
class ComputationError(MagnetAPIException):
    """Base exception for computation/calculation errors."""
    pass


class InvalidParameterError(ComputationError):
    """Raised when computation receives invalid parameters.
    
    Context should include:
        - parameter: Name of invalid parameter
        - value: Provided value
        - constraint: Constraint that was violated
    """
    pass


class ConvergenceError(ComputationError):
    """Raised when numerical computation fails to converge."""
    pass
```

**Update** `python_magnetapi/__init__.py` to export exceptions:
```python
from .exceptions import (
    MagnetAPIException,
    APIError,
    AuthenticationError,
    NotFoundError,
    APIRequestError,
    APIResponseError,
    ForbiddenError,
    ValidationError,
    InvalidDataError,
    MissingFieldError,
    ResourceError,
    ResourceCreationError,
    ResourceUpdateError,
    ResourceDeletionError,
    ComputationError,
    InvalidParameterError,
    ConvergenceError,
)

__all__ = [
    # ... existing exports ...
    "MagnetAPIException",
    "APIError",
    "AuthenticationError",
    # ... rest of exceptions ...
]
```

#### Step 1.2: Refactor utils.py

**Current pattern to replace:**
```python
# BEFORE:
if r.status_code != 200:
    print(response["detail"])
    return None
```

**New pattern:**
```python
# AFTER:
if r.status_code == 401 or r.status_code == 403:
    raise AuthenticationError(
        "Authentication failed - check MAGNETDB_API_KEY",
        status_code=r.status_code,
        url=r.url
    )
elif r.status_code == 404:
    raise NotFoundError(
        f"{mtype} with id {id} not found",
        status_code=r.status_code,
        url=r.url,
        resource_type=mtype,
        resource_id=id
    )
elif r.status_code != 200:
    detail = response.get("detail", "Unknown error") if isinstance(response, dict) else "Unknown error"
    raise APIResponseError(
        f"API request failed: {detail}",
        status_code=r.status_code,
        url=r.url,
        response=response
    )
```

**Functions to update in utils.py:**
- `get_list()` - Replace print + return None
- `get_object()` - Replace print + return None
- `create_object()` - Replace print + return None
- `update_object()` - Replace print + return None
- `del_object()` - Replace print statements
- `add_data_to_object()` - Replace print + return None
- `get_data()` - Replace print + return None
- `post_data()` - Replace print + return None
- All other utility functions with error handling

**Optional: Add helper function for consistent API error handling:**
```python
def _handle_response_error(response, status_code, url, context_msg=""):
    """Helper to handle API response errors consistently."""
    if status_code == 401 or status_code == 403:
        raise AuthenticationError(
            f"Authentication failed{': ' + context_msg if context_msg else ''}",
            status_code=status_code,
            url=url
        )
    elif status_code == 404:
        raise NotFoundError(
            f"Resource not found{': ' + context_msg if context_msg else ''}",
            status_code=status_code,
            url=url
        )
    elif status_code != 200:
        detail = response.get("detail", "Unknown error") if isinstance(response, dict) else "Unknown error"
        raise APIResponseError(
            f"API request failed: {detail}{': ' + context_msg if context_msg else ''}",
            status_code=status_code,
            url=url,
            response=response
        )
```

#### Step 1.3: Create Basic Tests

Create `tests/test_exceptions.py`:

```python
"""Tests for custom exceptions."""

import pytest
from python_magnetapi.exceptions import (
    MagnetAPIException,
    APIError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    InvalidParameterError,
)


def test_base_exception():
    """Test base MagnetAPIException."""
    exc = MagnetAPIException("Test error")
    assert str(exc) == "Test error"
    assert exc.message == "Test error"
    assert exc.context == {}


def test_exception_with_context():
    """Test exception with context."""
    exc = MagnetAPIException("Test error", status_code=404, url="http://example.com")
    assert "Test error" in str(exc)
    assert "status_code=404" in str(exc)
    assert "url=http://example.com" in str(exc)
    assert exc.context["status_code"] == 404


def test_authentication_error():
    """Test AuthenticationError is subclass of APIError."""
    exc = AuthenticationError("Auth failed", status_code=401)
    assert isinstance(exc, APIError)
    assert isinstance(exc, MagnetAPIException)


def test_not_found_error():
    """Test NotFoundError with resource context."""
    exc = NotFoundError(
        "Magnet not found",
        resource_type="magnet",
        resource_id=123
    )
    assert "Magnet not found" in str(exc)
    assert exc.context["resource_type"] == "magnet"


def test_validation_error():
    """Test ValidationError hierarchy."""
    exc = InvalidParameterError(
        "Invalid parameter",
        parameter="current",
        value=-100,
        constraint="must be positive"
    )
    assert isinstance(exc, ValidationError)
    assert exc.context["parameter"] == "current"


def test_exception_catching():
    """Test catching exceptions by hierarchy."""
    # Can catch specific type
    with pytest.raises(AuthenticationError):
        raise AuthenticationError("Auth error")
    
    # Can catch by parent type
    with pytest.raises(APIError):
        raise AuthenticationError("Auth error")
    
    # Can catch by base type
    with pytest.raises(MagnetAPIException):
        raise AuthenticationError("Auth error")
```

---

### Phase 2: Core Integration (Important)

#### Step 2.1: Update CLI Error Handling

Refactor `python_magnetapi/cli.py`:

**Add top-level error handler in main():**
```python
def main():
    """Main CLI entry point with comprehensive error handling."""
    try:
        # ... existing argument parsing ...
        
        # ... existing CLI logic ...
        
    except AuthenticationError as e:
        console.print(f"[red]Authentication Error:[/red] {e.message}", style="bold")
        if e.context:
            console.print(f"[dim]{e.context}[/dim]")
        console.print("\n[yellow]Tip:[/yellow] Check your MAGNETDB_API_KEY environment variable")
        sys.exit(2)
        
    except NotFoundError as e:
        console.print(f"[yellow]Not Found:[/yellow] {e.message}")
        if "resource_type" in e.context and "resource_id" in e.context:
            console.print(f"  Resource: {e.context['resource_type']} (ID: {e.context['resource_id']})")
        sys.exit(3)
        
    except ForbiddenError as e:
        console.print(f"[red]Access Forbidden:[/red] {e.message}")
        console.print("[yellow]Tip:[/yellow] You may not have permission for this operation")
        sys.exit(4)
        
    except APIError as e:
        console.print(f"[red]API Error:[/red] {e.message}", style="bold")
        if e.context:
            console.print(f"[dim]Details: {e.context}[/dim]")
        sys.exit(5)
        
    except ValidationError as e:
        console.print(f"[yellow]Validation Error:[/yellow] {e.message}")
        if "field" in e.context:
            console.print(f"  Field: {e.context['field']}")
        sys.exit(6)
        
    except ComputationError as e:
        console.print(f"[red]Computation Error:[/red] {e.message}")
        if e.context:
            console.print(f"[dim]Details: {e.context}[/dim]")
        sys.exit(7)
        
    except MagnetAPIException as e:
        console.print(f"[red]Error:[/red] {e.message}", style="bold")
        sys.exit(1)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
        
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", style="bold")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(99)
```

**Replace generic RuntimeError throughout cli.py:**
```python
# BEFORE:
raise RuntimeError(f"{args.server} : wrong credentials - check MAGNETDB_API_KEY")

# AFTER:
raise AuthenticationError(
    "Wrong credentials",
    server=args.server,
    hint="Check MAGNETDB_API_KEY environment variable"
)
```

#### Step 2.2: Update Domain Modules

For each domain module (`part.py`, `magnet.py`, `site.py`, `record.py`, `material.py`, `geometry.py`):

**Replace generic RuntimeError:**
```python
# BEFORE:
raise RuntimeError(
    f"part/create: unexpected type for material (type={type(mat)})"
)

# AFTER:
raise InvalidDataError(
    "Unexpected type for material",
    field="material",
    expected="str or dict",
    received=type(mat).__name__
)
```

**Add validation for required fields:**
```python
# BEFORE: Silent assumption that field exists

# AFTER:
if "name" not in data:
    raise MissingFieldError(
        "Name is required",
        field="name",
        resource_type="part"
    )
```

#### Step 2.3: Add Comprehensive Tests

Expand `tests/test_exceptions.py` with integration tests:

```python
def test_utils_get_object_not_found(mocker):
    """Test get_object raises NotFoundError for 404."""
    # Mock requests to return 404
    # Verify NotFoundError is raised with correct context
    pass


def test_utils_authentication_error(mocker):
    """Test API functions raise AuthenticationError for 401/403."""
    pass


def test_cli_error_handling(capsys):
    """Test CLI handles exceptions gracefully."""
    pass
```

---

### Phase 3: Polish & Advanced (Optional)

#### Step 3.1: Update Computation Modules

For `hoop_stress.py`, `hoop_stress_parallel.py`, `flow_params.py`, `inductances.py`:

**Replace generic ValueError:**
```python
# BEFORE:
raise ValueError("At least one current array must be provided.")

# AFTER:
raise InvalidParameterError(
    "At least one current array must be provided",
    parameter="currents",
    constraint="must provide I, I_dict, or I2"
)
```

**Don't silently catch exceptions:**
```python
# BEFORE:
try:
    result = compute_something()
except:
    pass  # Silent failure

# AFTER:
try:
    result = compute_something()
except Exception as e:
    raise ComputationError(
        f"Computation failed: {e}",
        operation="compute_something"
    ) from e
```

#### Step 3.2: Add Retry Logic (Optional)

Add retry decorator for transient failures in utils.py:

```python
from functools import wraps
import time


def retry_on_transient_error(max_attempts=3, backoff=1.0):
    """Decorator to retry API calls on transient errors.
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff: Backoff multiplier (exponential backoff)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except APIRequestError as e:
                    # Only retry on network errors, not auth/validation
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    time.sleep(backoff * (2 ** attempt))
                except APIResponseError as e:
                    # Retry on 5xx server errors
                    if "status_code" in e.context and 500 <= e.context["status_code"] < 600:
                        attempt += 1
                        if attempt >= max_attempts:
                            raise
                        time.sleep(backoff * (2 ** attempt))
                    else:
                        raise
            return None
        return wrapper
    return decorator


# Usage:
@retry_on_transient_error(max_attempts=3)
def get_list(...):
    # existing implementation
    pass
```

#### Step 3.3: Documentation

Add to docs:

1. **docs/error_handling.rst** - New documentation file:
```rst
Error Handling
==============

Exception Hierarchy
-------------------

python-magnetapi uses a hierarchy of custom exceptions...

[Document all exception types, when they're raised, how to catch them]

Common Error Scenarios
----------------------

Authentication Errors
~~~~~~~~~~~~~~~~~~~~~

[How to handle auth errors, check credentials, etc.]

Resource Not Found
~~~~~~~~~~~~~~~~~~

[How to handle 404s, verify IDs, etc.]

Troubleshooting Guide
---------------------

[Common errors and solutions]
```

2. Update **docs/usage.rst** with error handling examples

3. Update **docs/api/** module docs with "Raises" sections in docstrings

---

## Implementation Guidelines

### Code Style
- All exception classes should have comprehensive docstrings
- Always include context in exceptions (status_code, url, resource info)
- Use Rich console for CLI error display (colors, formatting)
- Maintain backwards compatibility where possible

### Testing Strategy
- Unit tests for all exception classes
- Integration tests for utils.py error handling
- CLI error handler tests with mocked errors
- Edge case tests (network failures, malformed responses)

### Migration Considerations
- **Breaking change**: Functions that returned `None` will now raise exceptions
- Update all calling code to handle exceptions instead of checking for `None`
- Consider adding deprecation warnings if backwards compatibility needed

### Documentation Requirements
- Update all docstrings with "Raises" sections
- Add error handling example to README
- Create troubleshooting guide
- Add API reference for exceptions

---

## Success Criteria

✅ **Implementation Complete When:**
1. Custom exception hierarchy exists in `exceptions.py`
2. All utils.py functions raise exceptions instead of print/return None
3. CLI has comprehensive error handler with user-friendly messages
4. All domain modules use appropriate exception types
5. Test coverage for exceptions ≥ 90%
6. Documentation includes error handling guide
7. All existing tests pass with new error handling
8. No more generic `RuntimeError` or `ValueError` in codebase

✅ **Quality Metrics:**
- Zero `print()` statements for errors (use exceptions/logging)
- Zero `return None` on errors (raise exceptions)
- All exceptions include context
- User-friendly error messages in CLI
- Proper exit codes for different error types

---

## Testing Checklist

- [ ] All exception classes instantiate correctly
- [ ] Exception context is preserved and formatted properly
- [ ] utils.py raises correct exception types for different status codes
- [ ] CLI error handler catches and displays all exception types
- [ ] Domain modules raise appropriate exceptions
- [ ] Computation modules raise InvalidParameterError for bad inputs
- [ ] Integration test: Full CLI command with API error
- [ ] Integration test: Full CLI command with auth error
- [ ] Integration test: Full CLI command with not found error
- [ ] Exception messages are clear and actionable
- [ ] All docstrings updated with "Raises" sections

---

## References

**Related Files:**
- `python_magnetapi/exceptions.py` (new)
- `python_magnetapi/__init__.py` (update exports)
- `python_magnetapi/utils.py` (major refactor)
- `python_magnetapi/cli.py` (add error handler)
- `tests/test_exceptions.py` (new)

**Python Best Practices:**
- PEP 8: Exception naming conventions
- Use exception chaining (`raise ... from e`)
- Provide actionable error messages
- Include context for debugging

**Related Tasks:**
- Logging framework (should use logging for debugging, exceptions for errors)
- Type hints (exception raises should be in type hints when Python 3.11+)

---

## Notes for Implementation

1. **Start with exceptions.py** - Get the foundation right first
2. **Test each exception type** - Ensure hierarchy works correctly
3. **Refactor utils.py incrementally** - One function at a time, test each
4. **Update CLI last** - Requires utils.py refactor to be complete
5. **Add retry logic separately** - Don't complicate initial implementation

## Document Version

**Version**: 1.0  
**Created**: 2026-03-12  
**Task**: Error Handling and Exception Framework  
**Priority**: Tier 1 (High Impact, Foundation)  
**Status**: Ready for implementation
