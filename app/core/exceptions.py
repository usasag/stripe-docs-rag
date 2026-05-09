class AppError(Exception):
    """Base application exception."""


class SessionNotFoundError(AppError):
    """Raised when a session identifier does not exist."""


class RateLimitError(AppError):
    """Raised when a client exceeds rate limits."""


class AuthenticationError(AppError):
    """Raised when authentication fails."""


class IngestJobNotFoundError(AppError):
    """Raised when an ingest job ID does not exist."""


class EvalDatasetError(AppError):
    """Raised when an eval dataset is malformed or missing."""
