"""Custom exception classes for the application."""


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AuthorizationError(AppException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status_code=403)


class NotFoundError(AppException):
    """Raised when a resource is not found."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationError(AppException):
    """Raised when input validation fails."""

    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, status_code=422)


class BusinessRuleError(AppException):
    """Raised when a business rule is violated."""

    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class StockError(BusinessRuleError):
    """Raised for stock-related errors (insufficient, expired, etc.)."""
    pass


class InvoiceError(BusinessRuleError):
    """Raised for invoice-related errors."""
    pass
