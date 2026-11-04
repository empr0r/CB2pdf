"""Errors that callers can distinguish without parsing diagnostic messages."""


class ConversionError(Exception):
    """A controlled conversion failure; the source must remain available."""


class ArchiveFormatError(ConversionError):
    """The signature does not identify a supported archive."""


class ArchiveCorruptionError(ConversionError):
    """Archive metadata, member data, or integrity checks are invalid."""


class UnsafeArchiveError(ConversionError):
    """An unsafe name, link, duplicate name, or encrypted member was encountered."""


class MissingDependencyError(ConversionError):
    """An optional library or archive backend is unavailable."""


class ResourceLimitError(ConversionError):
    """An enforced resource limit was exceeded."""


class ImageDecodeError(ConversionError):
    """A selected image is invalid or cannot be preserved by the requested policy."""


class PdfGenerationError(ConversionError):
    """Image embedding or PDF finalization failed."""


class PdfVerificationError(ConversionError):
    """The finalized document failed structural or completeness verification."""


class OutputCollisionError(ConversionError):
    """An output or archival destination is already occupied."""


class SourceArchivalError(ConversionError):
    """The PDF was committed, but source archival did not finish."""


class CancelledError(ConversionError):
    """Cooperative cancellation was requested before commit."""
