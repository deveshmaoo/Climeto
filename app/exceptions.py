# HRMSV3_optimized/app/exceptions.py
"""Custom exceptions for the application."""

class HRMSError(Exception):
    """Base exception for HRMS application."""
    pass

class ResourceNotFoundError(HRMSError):
    """Raised when a requested resource is not found."""
    pass

class ValidationError(HRMSError):
    """Raised when data validation fails."""
    pass

class AuthorizationError(HRMSError):
    """Raised when user doesn't have required permissions."""
    pass

class DatabaseError(HRMSError):
    """Raised when database operations fail."""
    pass