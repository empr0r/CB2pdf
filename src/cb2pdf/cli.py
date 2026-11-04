"""The argparse interface; validation and exit-code policy live at this boundary."""

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .archives import ArchiveReader
from .config import ConversionConfig, Quality, ResourceLimits
from .errors import ConversionError, ResourceLimitError
from .images import inspect_member
from .reporting import configure_logging, write_report
from .scheduler import discover_jobs, run_batch

logger = logging.getLogger(__name__)


def dimensions(value: str) -> tuple[int, int]:
    try:
        components = value.lower().split("x")
        if len(components) == 1:
            components *= 2
        width, height = map(int, components)
        if width <= 0 or height <= 0:
            raise ValueError
        return width, height
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use a positive N or WIDTHxHEIGHT") from exc


def rgb(value: str) -> tuple[int, int, int]:
    try:
        value = value.removeprefix("#")
        if len(value) != 6:
            raise ValueError
        return (int(value[:2], 16), int(value[2:4], 16), int(value[4:], 16))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("background must be a six-digit RGB hex color") from exc


def add_common(parser: argparse.ArgumentParser) -> None:
    logging_options = parser.add_mutually_exclusive_group()
    logging_options.add_argument("-v", "--verbose", action="store_true")
    logging_options.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("--log-file", type=Path)
    parser.add_argument("--json-logs", action="store_true")
    defaults = ResourceLimits()
    for name in defaults.__dataclass_fields__:
        parser.add_argument(
            "--" + name.replace("_", "-"),
            type=float if name == "max_compression_ratio" else int,
            default=getattr(defaults, name),
            help=f"resource ceiling (default: {getattr(defaults, name)})",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cb2pdf", description="Convert comic archives safely to PDF")
    parser.add_argument("--version", action="version", version=f"cb2pdf {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    conversion = commands.add_parser("convert", help="convert files or directories")
    conversion.add_argument("inputs", type=Path, nargs="+")
    conversion.add_argument("--recursive", action="store_true")
    conversion.add_argument("-o", "--output", type=Path, help="output directory")
    conversion.add_argument("--quality", choices=[q.value for q in Quality], default="lossless")
    conversion.add_argument("--max-size", type=dimensions)
    conversion.add_argument("--upscale", action="store_true")
    conversion.add_argument("--jpeg-quality", type=int)
    conversion.add_argument("--flatten-alpha", action="store_true")
    conversion.add_argument("--background", type=rgb, default=(255, 255, 255))
    conversion.add_argument("--dpi", type=float)
    conversion.add_argument("--page-size", choices=("a4", "letter"))
    conversion.add_argument("--page-dimensions", type=dimensions, help="WIDTHxHEIGHT in PDF points")
    conversion.add_argument("--frames", choices=("all", "reject"), default="all")
    conversion.add_argument("--ordering", choices=("natural", "lexical"), default="natural")
    conversion.add_argument("--decode-verify", action="store_true")
    conversion.add_argument("--workers", type=int, default=1)
    conversion.add_argument("--memory-budget-mb", type=int)
    conversion.add_argument("--fail-fast", action="store_true")
    conversion.add_argument("--overwrite", action="store_true",
                            help="explicitly replace existing PDFs")
    originals = conversion.add_mutually_exclusive_group()
    originals.add_argument("--keep-original", action="store_true", help="default source policy")
    originals.add_argument("--move-original", type=Path)
    conversion.add_argument("--dry-run", action="store_true")
    conversion.add_argument("--report", type=Path, help="write an exclusive JSON batch report")
    for name in ("title", "author", "subject"):
        conversion.add_argument("--" + name)
    conversion.add_argument("--keywords", nargs="*", default=[])
    add_common(conversion)
    inspection = commands.add_parser("inspect", help="inspect archive metadata and image frames")
    inspection.add_argument("input", type=Path)
    inspection.add_argument("--decode-verify", action="store_true")
    add_common(inspection)
    benchmark = commands.add_parser("benchmark", help="run a reproducible synthetic benchmark")
    benchmark.add_argument("--output", type=Path, default=Path("benchmark-results.json"))
    benchmark.add_argument("--trials", type=int, default=3)
    benchmark.add_argument("--workers", type=int, default=1)
    benchmark.add_argument("--quick", action="store_true", help="small smoke workload")
    return parser


def configuration(args: argparse.Namespace) -> ConversionConfig:
    limits = ResourceLimits(**{name: getattr(args, name)
                            for name in ResourceLimits.__dataclass_fields__})
    page_size = {"a4": (595.276, 841.89), "letter": (612.0, 792.0)}.get(args.page_size)
    if args.page_size and args.page_dimensions:
        raise ValueError("use only one of --page-size and --page-dimensions")
    return ConversionConfig(
        quality=Quality(args.quality), max_size=args.max_size, upscale=args.upscale,
        jpeg_quality=args.jpeg_quality, background=args.background,
        flatten_alpha=args.flatten_alpha, dpi=args.dpi,
        page_size=args.page_dimensions or page_size, frames=args.frames, ordering=args.ordering,
        decode_verify=args.decode_verify, overwrite=args.overwrite,
        move_original=args.move_original, dry_run=args.dry_run, title=args.title,
        author=args.author, subject=args.subject, keywords=tuple(args.keywords), limits=limits,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "benchmark":
            from .benchmark import run_benchmark

            run_benchmark(args.output, args.trials, args.workers, args.quick)
            print(f"Benchmark results: {args.output}")
            return 0
        configure_logging(args.verbose, args.quiet, json_logs=args.json_logs)
        if args.command == "inspect":
            if args.log_file is not None and args.log_file.resolve() == args.input.resolve():
                raise ValueError("log file conflicts with input")
            configure_logging(args.verbose, args.quiet, args.log_file, args.json_logs)
            limits = ResourceLimits(
                **{name: getattr(args, name) for name in ResourceLimits.__dataclass_fields__}
            )
            config = ConversionConfig(limits=limits, decode_verify=args.decode_verify)
            with ArchiveReader(args.input, limits) as archive:
                images = []
                page_count = 0
                for member in archive.pages():
                    frames = inspect_member(archive, member, config)
                    page_count += len(frames)
                    if page_count > limits.max_pages:
                        raise ResourceLimitError("inspection page count exceeds configured limit")
                    images.append({
                        "member": member.name, "bytes": member.size,
                        "frames": [asdict(info) for info in frames],
                    })
                print(json.dumps({
                    "format": archive.format, "members": len(archive.infos),
                    "images": images, "warnings": archive.warnings,
                }, indent=2, ensure_ascii=True))
            return 0
        config = configuration(args)
        jobs = discover_jobs(args.inputs, args.output, args.recursive, config.move_original)
        if not jobs:
            logger.error("no CBZ or CBR archives found")
            return 1
        protected = {p.resolve() for job in jobs for p in (job.source, job.output)}
        if config.move_original is not None:
            protected.add(config.move_original.resolve())
            protected.update((config.move_original / job.source.name).resolve() for job in jobs)
        for name in ("report", "log_file"):
            sidecar = getattr(args, name)
            if sidecar is not None and sidecar.resolve() in protected:
                raise ValueError(
                    f"{name} path conflicts with a source, PDF, or archival destination")
        if args.log_file is not None and args.report is not None:
            if args.log_file.resolve() == args.report.resolve():
                raise ValueError("log file and report paths conflict")
        if args.report is not None:
            if args.report.exists() or args.report.is_symlink():
                raise ValueError("report already exists; choose a new report filename")
        configure_logging(
            args.verbose, args.quiet, None if config.dry_run else args.log_file, args.json_logs,
        )
        results = []
        for result in run_batch(jobs, config, args.workers, args.memory_budget_mb, args.fail_fast):
            results.append(result)
            log = logger.info if result.ok else logger.error
            log(
                "[%d/%d] %s: %s; %d pages; %.3fs; %d -> %d bytes; normalized %d%s",
                len(results), len(jobs), Path(result.source).name, result.status.value,
                len(result.pages), result.duration_seconds, result.source_bytes,
                result.output_bytes, result.normalized_pages,
                f"; {result.error_type}: {result.error}" if result.error else "",
                extra={
                    "archive": Path(result.source).name, "status": result.status.value,
                    "page_count": len(result.pages), "duration_seconds": result.duration_seconds,
                    "source_bytes": result.source_bytes, "output_bytes": result.output_bytes,
                },
            )
            for warning in result.warnings:
                logger.warning("%s: %s", Path(result.source).name, warning)
        if args.report is not None and not config.dry_run:
            write_report(args.report, results)
        logger.info(
            "completed: %d successful; %d failed",
            sum(r.ok for r in results), sum(not r.ok for r in results),
        )
        return 0 if all(r.ok for r in results) else 1
    except KeyboardInterrupt:
        logger.error("interrupted; active workers cancelled before commit where possible")
        return 130
    except (ConversionError, OSError, ValueError) as exc:
        print(f"cb2pdf: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
