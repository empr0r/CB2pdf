"""Collision-safe filesystem commits with explicit, limited transaction guarantees."""

import os
import shutil
import tempfile
from pathlib import Path
from types import TracebackType
from typing import BinaryIO

from .errors import OutputCollisionError, SourceArchivalError


def fingerprint(path: Path) -> tuple[int, int, int, int]:
    info = path.stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def sync_directory(directory: Path) -> None:
    """Sync directory entries on POSIX. Windows has no equivalent portable API."""
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class OutputTransaction:
    """Own a unique target-filesystem temporary; publish only after verification.

    No-overwrite commit uses an atomic exclusive hard link. Filesystems without hard
    links fail safely; no check-then-rename fallback may overwrite another process.
    """

    def __init__(self, destination: Path, overwrite: bool = False) -> None:
        self.destination = destination
        self.overwrite = overwrite
        self.temporary: Path | None = None
        self.stream: BinaryIO | None = None
        self.committed = False

    def __enter__(self) -> "OutputTransaction":
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        if not self.overwrite and os.path.lexists(self.destination):
            raise OutputCollisionError(f"destination already exists: {self.destination}")
        descriptor, name = tempfile.mkstemp(
            prefix=".cb2pdf-", suffix=".cb2pdf-part", dir=self.destination.parent
        )
        self.temporary = Path(name)
        self.stream = os.fdopen(descriptor, "w+b")
        return self

    def finish_writing(self) -> Path:
        assert self.stream is not None and self.temporary is not None
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.stream.close()
        self.stream = None
        return self.temporary

    def commit(self) -> None:
        assert self.temporary is not None and self.stream is None
        try:
            if self.overwrite:
                os.replace(self.temporary, self.destination)
            else:
                os.link(self.temporary, self.destination)
        except FileExistsError as exc:
            raise OutputCollisionError(
                f"destination won a concurrent race: {self.destination}") from exc
        self.committed = True
        if not self.overwrite:
            self.temporary.unlink()
        self.temporary = None
        sync_directory(self.destination.parent)

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if self.stream is not None:
                self.stream.close()
        finally:
            if self.temporary is not None:
                self.temporary.unlink(missing_ok=True)


def archive_source(
    source: Path, directory: Path, original_fingerprint: tuple[int, int, int, int]
) -> Path:
    """Copy, fsync and exclusively commit the source, then unlink its old name.

    Works across filesystems, never overwrites an archive destination. A failure after
    copy commit can leave two originals; the verified PDF remains committed throughout.
    The caller owns source files/directories; concurrent external mutation is unsupported.
    """
    destination = directory / source.name
    try:
        if source.is_symlink() or fingerprint(source) != original_fingerprint:
            raise SourceArchivalError("source changed during conversion; retained original")
        if source.resolve() == destination.resolve():
            raise SourceArchivalError("source archival destination equals source")
        with OutputTransaction(destination) as transaction:
            assert transaction.stream is not None
            with source.open("rb") as stream:
                shutil.copyfileobj(stream, transaction.stream, length=1024**2)
            assert transaction.temporary is not None
            shutil.copystat(source, transaction.temporary)
            transaction.finish_writing()
            if fingerprint(source) != original_fingerprint:
                raise SourceArchivalError("source changed while copying; retained original")
            transaction.commit()
        if fingerprint(source) != original_fingerprint:
            raise SourceArchivalError("source changed before removal; both copies retained")
        source.unlink()
        sync_directory(source.parent)
        return destination
    except SourceArchivalError:
        raise
    except (OSError, OutputCollisionError) as exc:
        raise SourceArchivalError(
            f"PDF committed; source archival incomplete ({destination}): {exc}"
        ) from exc
