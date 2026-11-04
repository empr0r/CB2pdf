"""Validated policies shared by the CLI and Python API."""

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from pathlib import Path


class Quality(str, Enum):
    LOSSLESS = "lossless"
    BALANCED = "balanced"
    SMALL = "small"


@dataclass(frozen=True)
class ResourceLimits:
    max_members: int = 10_000
    max_pages: int = 10_000
    max_member_bytes: int = 128 * 1024**2
    max_total_bytes: int = 4 * 1024**3
    max_compression_ratio: float = 1000.0
    max_pixels: int = 40_000_000
    max_pdf_input_bytes: int = 512 * 1024**2
    max_output_bytes: int = 2 * 1024**3

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if name == "max_compression_ratio":
                valid = isinstance(value, (int, float)) and not isinstance(value, bool)
                valid = valid and isfinite(value) and value > 0
            else:
                valid = isinstance(value, int) and not isinstance(value, bool) and value > 0
            if not valid:
                raise ValueError(f"{name} must be finite and positive")


@dataclass(frozen=True)
class ConversionConfig:
    quality: Quality = Quality.LOSSLESS
    max_size: tuple[int, int] | None = None
    upscale: bool = False
    jpeg_quality: int | None = None
    background: tuple[int, int, int] = (255, 255, 255)
    flatten_alpha: bool = False
    dpi: float | None = None
    page_size: tuple[float, float] | None = None
    frames: str = "all"
    ordering: str = "natural"
    decode_verify: bool = False
    overwrite: bool = False
    move_original: Path | None = None
    dry_run: bool = False
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: tuple[str, ...] = ()
    limits: ResourceLimits = field(default_factory=ResourceLimits)

    def __post_init__(self) -> None:
        if not isinstance(self.quality, Quality):
            raise ValueError("quality must be a Quality enum")
        for name in ("max_size", "page_size"):
            value = getattr(self, name)
            if value is not None and (
                len(value) != 2 or any(not isfinite(x) or x <= 0 for x in value)
            ):
                raise ValueError(f"{name} requires two finite positive dimensions")
        if self.max_size is not None and any(type(x) is not int for x in self.max_size):
            raise ValueError("max_size dimensions must be integers")
        if self.dpi is not None and (not isfinite(self.dpi) or self.dpi <= 0):
            raise ValueError("dpi must be finite and positive")
        if self.jpeg_quality is not None and not 1 <= self.jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100")
        if self.jpeg_quality is not None and type(self.jpeg_quality) is not int:
            raise ValueError("jpeg_quality must be an integer")
        if self.quality is Quality.LOSSLESS and self.jpeg_quality is not None:
            raise ValueError("jpeg_quality requires balanced or small quality")
        if len(self.background) != 3 or any(not 0 <= c <= 255 for c in self.background):
            raise ValueError("background must contain three channels between 0 and 255")
        if any(type(c) is not int for c in self.background):
            raise ValueError("background channels must be integers")
        if self.frames not in ("all", "reject"):
            raise ValueError("frames must be all or reject")
        if self.ordering not in ("natural", "lexical"):
            raise ValueError("ordering must be natural or lexical")
        if self.upscale and self.max_size is None:
            raise ValueError("upscale requires explicit max_size")

    @property
    def effective_max_size(self) -> tuple[int, int] | None:
        if self.max_size is not None:
            return self.max_size
        if self.quality is Quality.SMALL:
            return (1600, 1600)
        return None

    @property
    def effective_jpeg_quality(self) -> int:
        if self.jpeg_quality is not None:
            return self.jpeg_quality
        return 75 if self.quality is Quality.SMALL else 90

    @property
    def estimated_worker_bytes(self) -> int:
        """Conservative scheduling estimate, not an operating-system memory limit."""
        return (
            self.limits.max_pdf_input_bytes * 3
            + self.limits.max_pixels * 16
            + self.limits.max_member_bytes * 2
        )
