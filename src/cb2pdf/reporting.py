"""Logging setup and atomic machine-readable batch reports."""

import json
import logging
import sys
from pathlib import Path
from typing import Any

from .models import ConversionResult
from .transactions import OutputTransaction


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "level": record.levelname, "logger": record.name, "message": record.getMessage(),
        }
        for field in (
            "archive", "status", "page_count", "duration_seconds", "source_bytes", "output_bytes",
        ):
            if hasattr(record, field):
                data[field] = getattr(record, field)
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=True)


def configure_logging(
    verbose: bool = False, quiet: bool = False, log_file: Path | None = None,
    json_logs: bool = False,
) -> None:
    logger = logging.getLogger("cb2pdf")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    logger.propagate = False
    logging.getLogger("img2pdf").setLevel(logging.DEBUG if verbose else logging.ERROR)
    formatter = JsonFormatter() if json_logs else logging.Formatter("%(levelname)s: %(message)s")
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.ERROR if quiet else logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)
    if log_file is not None:
        handler = logging.FileHandler(log_file, mode="x", encoding="utf-8")
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def write_report(path: Path, results: list[ConversionResult]) -> None:
    """Reports receive the same exclusive destination protection as PDFs."""
    data = {
        "schema_version": 1,
        "total": len(results),
        "successful": sum(r.ok for r in results),
        "failed": sum(not r.ok for r in results),
        "results": [r.to_dict() for r in results],
    }
    with OutputTransaction(path) as transaction:
        assert transaction.stream is not None
        transaction.stream.write(json.dumps(data, indent=2, ensure_ascii=True).encode("utf-8"))
        transaction.finish_writing()
        transaction.commit()
