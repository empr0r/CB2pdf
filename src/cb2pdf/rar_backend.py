"""Scoped RAR backend integration; no process-global rarfile patches.

rarfile 4.2 and 4.5 inserts ``--`` immediately after bsdtar's ``-f``. Bsdtar
interprets that token as the archive filename. Use its proper argument order
while retaining rarfile's bounded, seekable, checksum-checking pipe reader.
"""

from pathlib import Path
from typing import Any, BinaryIO

from .errors import MissingDependencyError


def validate_rar_backend(archive: Any, backend: Any) -> None:
    """Reject a known backend limitation before it can look like corrupt input."""
    import rarfile

    if (
        backend.setup["open_cmd"][0] == "BSDTAR_TOOL"
        and isinstance(archive._file_parser, rarfile.RAR3Parser)
        and archive.is_solid()
    ):
        raise MissingDependencyError(
            "bsdtar cannot decode solid RAR3/RAR4 archives; install unrar, unar, or 7z"
        )


def open_rar_member(archive: Any, info: Any, source: Path, backend: Any) -> BinaryIO:
    """Open one checked stream, repairing only bsdtar's command construction.

    Inputs have already passed member-name, encryption and size validation.
    The private PipeReader/parser interface is isolated here and tested against
    the supported rarfile floor and latest release. No filesystem extraction is
    used. Backward seeks retain rarfile's restart-and-read behavior.
    """
    import rarfile

    if backend.setup["open_cmd"][0] != "BSDTAR_TOOL" or info.compress_type == rarfile.RAR_M0:
        return archive.open(info)
    # Bsdtar treats member selectors as glob patterns, even in an argument list.
    # Quote metacharacters for its matcher, not a shell; shell execution is absent.
    selector = "".join("\\" + char if char in "\\[]*?" else char for char in info.filename)
    command = [rarfile.BSDTAR_TOOL, "-x", "--to-stdout", "-f",
               str(source.resolve()), "--", selector]
    return rarfile.PipeReader(archive._file_parser, info, command)
