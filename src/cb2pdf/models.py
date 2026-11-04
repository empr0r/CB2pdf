"""Typed records exchanged between pipeline stages."""

from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArchiveMember:
    index: int
    name: str
    size: int
    compressed_size: int


@dataclass(frozen=True)
class ImageMetadata:
    format: str
    mode: str
    width: int
    height: int
    frames: int
    orientation: int
    has_alpha: bool
    has_icc: bool
    is_animated: bool = False


@dataclass
class PageResult:
    member: str
    frame: int
    width: int
    height: int
    transformations: list[str] = field(default_factory=list)
    encoded_bytes: int = 0
    direct_stream_sha256: str | None = None
    rotation_degrees: int = 0


@dataclass(frozen=True)
class VerificationResult:
    expected_pages: int
    actual_pages: int
    size_bytes: int


class Status(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ARCHIVAL_FAILED = "pdf_committed_archival_incomplete"
    COMMIT_INCOMPLETE = "pdf_committed_durability_failed"
    DRY_RUN = "dry_run"
    CANCELLED = "cancelled"


@dataclass
class ConversionResult:
    source: str
    output: str
    status: Status = Status.FAILED
    source_bytes: int = 0
    output_bytes: int = 0
    duration_seconds: float = 0.0
    pages: list[PageResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error_type: str | None = None
    error: str | None = None
    archived_to: str | None = None
    verified: bool = False
    committed: bool = False
    source_retained: bool = True

    @property
    def ok(self) -> bool:
        return self.status in (Status.SUCCESS, Status.DRY_RUN)

    @property
    def normalized_pages(self) -> int:
        return sum(bool(p.transformations) for p in self.pages)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["page_count"] = len(self.pages)
        data["normalized_pages"] = self.normalized_pages
        data["skipped_pages"] = 0
        return data


@dataclass(frozen=True)
class ConversionJob:
    source: Path
    output: Path
