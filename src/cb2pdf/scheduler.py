"""Filesystem discovery and bounded archive-level scheduling."""

import threading
import unicodedata
from collections.abc import Iterable, Iterator
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path

from .config import ConversionConfig
from .converter import convert
from .errors import OutputCollisionError
from .models import ConversionJob, ConversionResult, Status
from .ordering import natural_key


def discover_jobs(
    inputs: Iterable[Path], output_directory: Path | None, recursive: bool = False,
    excluded_directory: Path | None = None,
) -> list[ConversionJob]:
    """Preserve directory structure under --output; reject batch destination collisions.

    Case-folded NFC destination checks intentionally use the conservative policy on
    every OS. This catches collisions before any worker can commit an output.
    """
    jobs = []
    seen_sources: set[Path] = set()
    seen_outputs: dict[str, Path] = {}
    excluded = excluded_directory.resolve() if excluded_directory else None
    for item in inputs:
        item = item.absolute()
        if item.is_file():
            candidates = [item]
            root = item.parent
        elif item.is_dir():
            candidates = [
                p for p in (item.rglob("*") if recursive else item.iterdir())
                if p.is_file() and p.suffix.casefold() in (".cbz", ".cbr")
            ]
            root = item
        else:
            raise FileNotFoundError(f"input does not exist or is not a regular file: {item}")
        for source in sorted(candidates, key=lambda p: natural_key(str(p))):
            resolved = source.resolve()
            if excluded is not None and resolved.is_relative_to(excluded):
                continue
            if resolved in seen_sources:
                continue
            seen_sources.add(resolved)
            output = source.with_suffix(".pdf")
            if output_directory is not None:
                output = output_directory / source.relative_to(root).with_suffix(".pdf")
            key = unicodedata.normalize("NFC", str(output.resolve())).casefold()
            if key in seen_outputs:
                raise OutputCollisionError(
                    f"batch output collision: {seen_outputs[key]} and {source} -> {output}"
                )
            seen_outputs[key] = source
            jobs.append(ConversionJob(source, output))
    source_paths = {job.source.resolve() for job in jobs}
    if any(job.output.resolve() in source_paths for job in jobs):
        raise OutputCollisionError("a PDF destination would replace a batch input")
    return jobs


def run_batch(
    jobs: list[ConversionJob], config: ConversionConfig, workers: int = 1,
    memory_budget_mb: int | None = None, fail_fast: bool = False,
) -> Iterator[ConversionResult]:
    """At most workers active futures; queue contains paths, never image payloads.

    Cancellation is cooperative between members and before commit. Native decoders and
    RAR subprocess reads cannot be forcibly interrupted by this thread scheduler.
    """
    if workers < 1:
        raise ValueError("workers must be positive")
    if memory_budget_mb is not None:
        effective = memory_budget_mb * 1024**2 // config.estimated_worker_bytes
        if effective < 1:
            raise ValueError("memory budget is below the estimated capacity of one worker")
        workers = min(workers, effective)
    cancel = threading.Event()
    executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cb2pdf")
    pending: dict[Future[ConversionResult], ConversionJob] = {}
    position = 0
    try:
        while position < len(jobs) or pending:
            while not cancel.is_set() and position < len(jobs) and len(pending) < workers:
                job = jobs[position]
                pending[executor.submit(convert, job.source, job.output, config, cancel)] = job
                position += 1
            if not pending:
                break
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                del pending[future]
                result = future.result()
                if fail_fast and not result.ok:
                    cancel.set()
                yield result
        for job in jobs[position:]:
            yield ConversionResult(
                str(job.source), str(job.output), Status.CANCELLED,
                error_type="CancelledError", error="not started after batch cancellation",
            )
    finally:
        cancel.set()
        executor.shutdown(wait=True, cancel_futures=True)
