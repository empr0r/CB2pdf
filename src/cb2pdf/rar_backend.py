"""Scoped RAR backend integration; no process-global rarfile patches.

rarfile 4.2 and 4.5 insert ``--`` immediately after bsdtar's ``-f``. Bsdtar
interprets that token as the archive filename. Use its proper argument order
while retaining rarfile's bounded, seekable, checksum-checking pipe reader.
"""

from pathlib import Path
import subprocess
from typing import Any, BinaryIO

from .errors import MissingDependencyError


def parse_sevenzip_decoders(information: str) -> frozenset[str]:
    """Read enabled RAR methods, rather than merely advertised archive formats.

    Distribution builds can list a RAR archive handler while omitting its RAR3
    decoder. Homebrew can omit all RAR decoders. Only decoder flags in the
    Codecs section establish that compressed members can actually be read.
    """
    codecs = False
    methods = set()
    for line in information.splitlines():
        if line.strip().endswith(":"):
            codecs = line.strip() == "Codecs:"
            continue
        fields = line.split()
        if codecs and len(fields) >= 3 and fields[-1] in ("Rar1", "Rar2", "Rar3", "Rar5"):
            if "D" in fields[-3]:
                methods.add(fields[-1])
    return frozenset(methods)


def sevenzip_decoders(backend: Any) -> frozenset[str]:
    """Inspect the selected executable once per archive, with a finite timeout."""
    import rarfile

    executable = getattr(rarfile, backend.setup["open_cmd"][0])
    try:
        result = subprocess.run([executable, "i"], capture_output=True, check=True,
                                encoding="utf-8", errors="replace", timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        raise MissingDependencyError(
            "cannot inspect 7-Zip RAR decoders; install a working full 7-Zip, unrar, or unar"
        ) from exc
    return parse_sevenzip_decoders(result.stdout)


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
    if backend.setup["open_cmd"][0] in ("SEVENZIP_TOOL", "SEVENZIP2_TOOL"):
        required = set()
        for info in archive.infolist():
            if not info.is_file() or info.compress_type == rarfile.RAR_M0:
                continue
            if isinstance(archive._file_parser, rarfile.RAR5Parser):
                required.add("Rar5")
            elif info.extract_version >= 29:
                required.add("Rar3")
            elif info.extract_version >= 20:
                required.add("Rar2")
            else:
                required.add("Rar1")
        if required:
            missing = required - sevenzip_decoders(backend)
            if missing:
                raise MissingDependencyError(
                    "selected 7-Zip build lacks RAR decoder(s): " + ", ".join(sorted(missing))
                    + "; install its RAR codec package, full 7-Zip, unrar, or unar"
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
