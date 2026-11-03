"""Signature-driven ZIP/RAR readers. Archive names are never extracted to disk."""

import io
import re
import stat
import struct
import threading
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO

from .config import ResourceLimits
from .errors import (
    ArchiveCorruptionError,
    ArchiveFormatError,
    CancelledError,
    ConversionError,
    MissingDependencyError,
    ResourceLimitError,
    UnsafeArchiveError,
)
from .models import ArchiveMember
from .ordering import natural_key, normalized_name

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
_RAR_LOCK = threading.Lock()


def check_cancelled(cancel: threading.Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise CancelledError("conversion cancelled before output commit")


def detect_format(path: Path) -> str:
    """Recognize ordinary ZIP and RAR signatures, including mislabeled inputs.

    Self-extracting executables are intentionally unsupported.
    """
    with path.open("rb") as stream:
        signature = stream.read(8)
    if signature.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "zip"
    if signature.startswith((b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00")):
        return "rar"
    raise ArchiveFormatError("expected a ZIP/CBZ or RAR/CBR signature")


def validate_member_name(name: str) -> str:
    normalized = normalized_name(name)
    parts = normalized.split("/")
    if (
        len(name) > 4096
        or any(ord(c) < 32 for c in name)
        or normalized.startswith("/")
        or re.match(r"^[A-Za-z]:", normalized)
        or any(part in ("..", ".") for part in parts)
        or ":" in normalized
    ):
        raise UnsafeArchiveError(f"unsafe archive member name: {name!r}")
    return normalized


def is_image_member(name: str) -> bool:
    parts = normalized_name(name).split("/")
    if any(part.startswith(".") or part.casefold() == "__macosx" for part in parts):
        return False
    return Path(parts[-1]).suffix.lower() in IMAGE_EXTENSIONS


def _preflight_zip(path: Path, limits: ResourceLimits) -> None:
    """Bound central-directory allocation before ZipFile constructs its member list."""
    with path.open("rb") as stream:
        stream.seek(0, io.SEEK_END)
        size = stream.tell()
        stream.seek(max(0, size - 65557))
        tail = stream.read()
        position = tail.rfind(b"PK\x05\x06")
        if position < 0 or len(tail) - position < 22:
            raise ArchiveCorruptionError("ZIP end-of-central-directory record is missing")
        record = struct.unpack_from("<4s4H2LH", tail, position)
        count, directory_bytes = record[4], record[5]
        if record[1] or record[2]:
            raise ArchiveFormatError("split ZIP archives are unsupported")
        if count == 65535 or directory_bytes == 0xFFFFFFFF:
            eocd_offset = size - len(tail) + position
            if eocd_offset < 20:
                raise ArchiveCorruptionError("ZIP64 locator is missing")
            stream.seek(eocd_offset - 20)
            locator = stream.read(20)
            if locator[:4] != b"PK\x06\x07":
                raise ArchiveCorruptionError("ZIP64 locator is missing")
            _, disk, offset, disks = struct.unpack("<4sLQL", locator)
            if disk or disks != 1:
                raise ArchiveFormatError("split ZIP64 archives are unsupported")
            stream.seek(offset)
            header = stream.read(56)
            if len(header) != 56 or header[:4] != b"PK\x06\x06":
                raise ArchiveCorruptionError("invalid ZIP64 directory record")
            fields = struct.unpack("<4sQ2H2L4Q", header)
            count, directory_bytes = fields[7], fields[8]
        if count > limits.max_members:
            raise ResourceLimitError(f"archive has {count} members; limit {limits.max_members}")
        if directory_bytes > 16 * 1024**2:
            raise ResourceLimitError("ZIP central directory exceeds 16 MiB metadata limit")


class ArchiveReader:
    """Own one archive handle and provide checked member streams.

    Each reader belongs to a single conversion worker. Declared limits apply to all
    members, including ignored metadata; actual size/CRC checks apply to page data.
    """

    def __init__(
        self, path: Path, limits: ResourceLimits, cancel: threading.Event | None = None
    ) -> None:
        self.path = path
        self.limits = limits
        self.cancel = cancel
        self.format = detect_format(path)
        self.handle: Any = None
        self.infos: list[Any] = []
        self.members: list[ArchiveMember] = []
        self.warnings: list[str] = []
        self.actual_bytes = 0
        self._rar_headers = 0
        self._rar_metadata_bytes = 0

    def __enter__(self) -> "ArchiveReader":
        try:
            if self.format == "zip":
                _preflight_zip(self.path, self.limits)
                self.handle = zipfile.ZipFile(self.path)
            else:
                try:
                    import rarfile
                except ImportError as exc:
                    raise MissingDependencyError("CBR requires: pip install 'cb2pdf[rar]'") from exc
                with _RAR_LOCK:
                    try:
                        rarfile.tool_setup()
                    except rarfile.RarCannotExec as exc:
                        raise MissingDependencyError(
                            "RAR decoding requires unrar, unar, 7z, or bsdtar on PATH; "
                            "consult docs/troubleshooting.md"
                        ) from exc
                self.handle = rarfile.RarFile(
                    self.path, errors="strict", part_only=True,
                    info_callback=self._check_rar_header,
                )
                if self.handle.needs_password():
                    raise UnsafeArchiveError("encrypted RAR archives are unsupported")
                if len(self.handle.volumelist()) > 1:
                    raise ArchiveFormatError("multi-volume RAR archives are unsupported")
            self._enumerate()
            return self
        except BaseException as exc:
            self.close()
            if isinstance(exc, (ConversionError, OSError, KeyboardInterrupt, SystemExit)):
                raise
            raise ArchiveCorruptionError(f"cannot inspect archive: {exc}") from exc

    def _check_rar_header(self, info: Any) -> None:
        """Stop RAR enumeration while parsing, rather than after unbounded allocation."""
        import rarfile

        check_cancelled(self.cancel)
        self._rar_headers += 1
        self._rar_metadata_bytes += getattr(info, "header_size", 0) or 0
        if self._rar_headers > self.limits.max_members + 100:
            raise ResourceLimitError(
                "RAR header count exceeds member limit plus 100 service records")
        if self._rar_metadata_bytes > 16 * 1024**2:
            raise ResourceLimitError("RAR headers exceed 16 MiB metadata limit")
        if info.type == rarfile.RAR_BLOCK_MAIN and info.flags & rarfile.RAR_MAIN_VOLUME:
            raise ArchiveFormatError("multi-volume RAR archives are unsupported")
        if getattr(info, "file_redir", None):
            raise UnsafeArchiveError("RAR link/redirection entries are unsupported")

    def _enumerate(self) -> None:
        total = 0
        names: set[str] = set()
        portable_names: set[str] = set()
        self.infos = self.handle.infolist()
        if len(self.infos) > self.limits.max_members:
            raise ResourceLimitError("archive member count exceeds configured limit")
        for index, info in enumerate(self.infos):
            check_cancelled(self.cancel)
            # ZipInfo.filename truncates NULs; validate its original spelling first.
            original_name = info.orig_filename if self.format == "zip" else info.filename
            name = validate_member_name(original_name)
            if name in names:
                raise UnsafeArchiveError(f"duplicate normalized member name: {name!r}")
            names.add(name)
            if name.casefold() in portable_names:
                self.warnings.append(f"case-ambiguous names ordered by spelling: {name!r}")
            portable_names.add(name.casefold())
            if self.format == "zip":
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode) or (
                    stat.S_IFMT(mode) and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))
                ):
                    raise UnsafeArchiveError(f"link or special archive member: {name!r}")
                encrypted = bool(info.flag_bits & 1)
                directory = info.is_dir()
            else:
                if info.is_symlink() or not (info.is_file() or info.is_dir()):
                    raise UnsafeArchiveError(f"link or special RAR member: {name!r}")
                encrypted = info.needs_password()
                directory = info.is_dir()
            if encrypted:
                raise UnsafeArchiveError(f"encrypted member: {name!r}")
            size, compressed = info.file_size, info.compress_size
            if size < 0 or compressed < 0:
                raise ArchiveCorruptionError(f"negative member size: {name!r}")
            total += size
            if size > self.limits.max_member_bytes or total > self.limits.max_total_bytes:
                raise ResourceLimitError(f"uncompressed size limit exceeded at {name!r}")
            if size / max(compressed, 1) > self.limits.max_compression_ratio:
                raise ResourceLimitError(f"compression ratio limit exceeded at {name!r}")
            if not directory:
                self.members.append(ArchiveMember(index, name, size, compressed))

    def pages(self, ordering: str = "natural") -> list[ArchiveMember]:
        selected = [m for m in self.members if is_image_member(m.name)]
        if ordering == "natural":
            return sorted(selected, key=lambda m: natural_key(m.name))
        return sorted(selected, key=lambda m: (normalized_name(m.name), m.name))

    @contextmanager
    def open(self, member: ArchiveMember) -> Iterator[BinaryIO]:
        try:
            with self.handle.open(self.infos[member.index]) as stream:
                yield stream
        except (ConversionError, OSError):
            raise
        except Exception as exc:
            raise ArchiveCorruptionError(f"cannot read {member.name!r}: {exc}") from exc

    def read(self, member: ArchiveMember) -> bytes:
        """Read one bounded member to EOF, enforcing declared size and backend CRC."""
        data = bytearray()
        with self.open(member) as stream:
            while True:
                check_cancelled(self.cancel)
                block = stream.read(min(1024**2, self.limits.max_member_bytes + 1 - len(data)))
                if not block:
                    break
                data.extend(block)
                if len(data) > member.size or len(data) > self.limits.max_member_bytes:
                    raise ResourceLimitError(f"actual member size exceeds limit: {member.name!r}")
        if len(data) != member.size:
            raise ArchiveCorruptionError(f"declared/actual size mismatch: {member.name!r}")
        self.actual_bytes += len(data)
        if self.actual_bytes > self.limits.max_total_bytes:
            raise ResourceLimitError("actual uncompressed image data exceeds total byte limit")
        return bytes(data)

    def close(self) -> None:
        if self.handle is not None:
            self.handle.close()
            self.handle = None

    def __exit__(self, *args: Any) -> None:
        self.close()
