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

    This typically occurs when:
    - MAGNETDB_API_KEY is not set
    - API key is invalid or expired
    - API returns 401 Unauthorized
    """

    pass


class AuthorizationError(APIError):
    """Raised when user lacks permission for an operation.

    This occurs when:
    - User is authenticated but doesn't have permission
    - API returns 403 Forbidden
    """

    pass


class ResourceNotFoundError(APIError):
    """Raised when a requested resource doesn't exist.

    This occurs when:
    - Specified object name/ID doesn't exist
    - API returns 404 Not Found
    """

    pass


class ResourceConflictError(APIError):
    """Raised when a resource already exists or conflicts.

    This occurs when:
    - Trying to create an object with duplicate name
    - API returns 409 Conflict
    """

    pass


class ValidationError(MagnetAPIException):
    """Raised when input data validation fails.

    This occurs when:
    - Required fields are missing
    - Data format is invalid
    - Business logic validation fails
    """

    pass


class NetworkError(APIError):
    """Raised when network communication fails.

    This occurs when:
    - Connection timeout
    - Server unreachable
    - DNS resolution fails
    """

    pass


class ServerError(APIError):
    """Raised when server returns 5xx error.

    This indicates a server-side problem that the client cannot fix.
    """

    pass
