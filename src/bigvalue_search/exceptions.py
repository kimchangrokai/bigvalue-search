"""Custom exceptions for BigValue search tool."""

from __future__ import annotations


class BigValueError(Exception):
    """Base exception for BigValue search tool."""


class GeocodingError(BigValueError):
    """Raised when geocoding fails."""


class AuthenticationError(BigValueError):
    """Raised when authentication fails."""


class APIError(BigValueError):
    """Raised when API request fails."""


class ConfigError(BigValueError):
    """Raised when configuration is invalid."""


class ExportError(BigValueError):
    """Raised when data export fails."""
