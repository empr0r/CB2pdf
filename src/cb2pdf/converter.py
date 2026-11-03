"""Single-archive orchestration; success requires a verified, committed complete PDF."""

import logging
import tempfile
import threading
import time
from pathlib import Path

from .archives import ArchiveReader, check_cancelled
from .config import ConversionConfig
from .errors import CancelledError, ConversionError, OutputCollisionError, SourceArchivalError
from .images import prepare_pages
from .models import ConversionResult, Status
from .pdf import verify_pdf, write_pdf
from .transactions import OutputTransaction, archive_source, fingerprint

logger = logging.getLogger(__name__)


def convert(
    source: Path,
    output: Path | None = None,
    config: ConversionConfig | None = None,
    cancel: threading.Event | None = None,
) -> ConversionResult:
    """Convert one archive, returning truthful partial-transaction outcomes.

    Known input, library and filesystem failures become results. KeyboardInterrupt and
    unexpected programming errors propagate so a scheduler cannot silently hide defects.
    """
    config = config or ConversionConfig()
    source = Path(source).absolute()
    output = Path(output).absolute() if output is not None else source.with_suffix(".pdf")
    result = ConversionResult(str(source), str(output))
    started = time.perf_counter()
    transaction = None
    try:
        check_cancelled(cancel)
        if source.is_symlink() or not source.is_file():
            raise ConversionError("source must be a regular file, not a symbolic link")
        if source.resolve() == output.resolve():
            raise OutputCollisionError("output destination equals source archive")
        original = fingerprint(source)
        result.source_bytes = original[2]
        if os_path_exists(output) and not config.overwrite:
            raise OutputCollisionError(f"destination already exists: {output}")
        with tempfile.TemporaryDirectory(prefix="cb2pdf-images-") as workspace:
            with ArchiveReader(source, config.limits, cancel) as archive:
                pages = prepare_pages(archive, config, Path(workspace))
                result.warnings.extend(archive.warnings)
                result.pages = [page.result for page in pages]
                if config.dry_run:
                    result.status = Status.DRY_RUN
                    return result
                with OutputTransaction(output, config.overwrite) as transaction:
                    assert transaction.stream is not None
                    write_pdf(pages, transaction.stream, config)
                    temporary = transaction.finish_writing()
                    verification = verify_pdf(temporary, pages)
                    result.verified = True
                    result.output_bytes = verification.size_bytes
                    check_cancelled(cancel)
                    if fingerprint(source) != original:
                        raise ConversionError("source changed during conversion; PDF not committed")
                    transaction.commit()
                    result.committed = True
        # Close the archive before moving it; required on Windows.
        if config.move_original is not None:
            archived = archive_source(source, config.move_original, original)
            result.archived_to = str(archived)
        result.status = Status.SUCCESS
    except (ConversionError, OSError) as exc:
        result.committed = transaction is not None and transaction.committed
        if isinstance(exc, SourceArchivalError):
            result.status = Status.ARCHIVAL_FAILED
        elif result.committed:
            result.status = Status.COMMIT_INCOMPLETE
        elif isinstance(exc, CancelledError):
            result.status = Status.CANCELLED
        result.error_type = type(exc).__name__
        result.error = str(exc)
        logger.debug("conversion failed: %s", source.name, exc_info=True)
    finally:
        result.duration_seconds = time.perf_counter() - started
        result.source_retained = source.exists()
    return result


def os_path_exists(path: Path) -> bool:
    """Also detect dangling symbolic links at destinations."""
    return path.exists() or path.is_symlink()
