"""Randomized fresh-process comparison of a frozen baseline, current code and reference fork.

Freeze the baseline package before edits, or supply a clean checkout's src directory.
No historical implementation ever receives user archives. Every output page is validated
outside conversion timing. Sequential archive workers may use bounded helper threads.
"""

import argparse
import hashlib
import json
import os
import random
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

from cb2pdf.benchmark import (
    environment_details, generate_workload, measure_child, process_usage,
    validate_outputs, write_json_exclusive,
)
if __package__:
    from .compare import WORKLOADS
else:
    from compare import WORKLOADS


def run_child(args: argparse.Namespace) -> None:
    import cb2pdf
    from cb2pdf.config import ConversionConfig
    from cb2pdf.converter import convert

    namespace = None
    if args.variant == "fork":
        reference = Path(__file__).parent / "reference/fork.py"
        namespace = {"__name__": "reference_benchmark", "__file__": str(args.run / "fork.py")}
        exec(compile(reference.read_text(), str(reference), "exec"), namespace)
    _, cpu_before = process_usage()
    started = time.perf_counter()
    errors = None
    if namespace is not None:
        namespace["main"]()
    else:
        results = [convert(p, config=ConversionConfig()) for p in sorted(args.run.glob("*.cbz"))]
        errors = sum(not result.ok for result in results)
    duration = time.perf_counter() - started
    rss, cpu_after = process_usage()
    cpu = cpu_after - cpu_before if cpu_before is not None and cpu_after is not None else None
    args.metrics.write_text(json.dumps({
        "conversion_wall_seconds": duration, "peak_rss_bytes": rss,
        "cpu_seconds": cpu, "cpu_percent": cpu / duration * 100 if cpu is not None else None,
        "reported_conversion_errors": errors,
        "package_path": str(Path(cb2pdf.__file__).resolve()),
        "environment": environment_details(),
    }))


def write_summary(report: dict, destination: Path) -> None:
    """Summarize medians and every observed fidelity/page count from raw evidence."""
    lines = [
        "# Performance comparison", "", report["methodology"], "",
        "| Workload | Variant | Median seconds | Peak RSS MiB | Exact ordered pixels | Pages |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for name in report["fixture_sha256"]:
        for variant in ("baseline", "fork", "optimized"):
            group = [r for r in report["results"]
                     if r["workload"] == name and r["variant"] == variant]
            durations = [r["conversion_wall_seconds"]
                         for r in group if "conversion_wall_seconds" in r]
            if not durations:
                continue
            rss = max(r.get("peak_rss_bytes") or 0 for r in group) / 1024**2
            # Show every observed count, so one good trial cannot hide a failure.
            exact = sorted({(r["exact_pixel_pages_in_correct_order"], r["expected_pages"])
                            for r in group})
            pages = sorted({(r["actual_pages"], r["expected_pages"]) for r in group})
            exact_text = ", ".join(f"{actual}/{expected}" for actual, expected in exact)
            pages_text = ", ".join(f"{actual}/{expected}" for actual, expected in pages)
            lines.append(
                f"| {name} | {variant} | {statistics.median(durations):.4f} | {rss:.1f} | "
                f"{exact_text} | {pages_text} |"
            )
    with destination.open("x") as stream:
        stream.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-src", type=Path, required=True)
    parser.add_argument("--workloads", choices=list(WORKLOADS), nargs="+", default=list(WORKLOADS))
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument(
        "--fixture-dirs", type=Path, nargs="+",
        help="read-only directories of prepared static-page CBZ fixtures; overrides workloads",
    )
    parser.add_argument("--output", type=Path, default=Path("benchmarks/reports/performance.json"))
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--variant", choices=("baseline", "optimized", "fork"))
    parser.add_argument("--run", type=Path)
    parser.add_argument("--metrics", type=Path)
    args = parser.parse_args()
    if args.child:
        run_child(args)
        return
    if args.trials < 3:
        parser.error("performance comparisons require at least three trials")
    if not (args.baseline_src / "cb2pdf/__init__.py").is_file():
        parser.error("baseline-src must contain the frozen cb2pdf package")
    if args.output.exists() or args.output.with_suffix(".md").exists():
        parser.error("choose a new output report path")
    baseline = args.baseline_src.resolve()
    current = Path(__file__).resolve().parents[1] / "src"
    order = random.Random(20261103)
    rows = []
    fixture_hashes = {}
    selected = [(name, None) for name in args.workloads]
    if args.fixture_dirs:
        selected = [(f"fixture-{index + 1}", directory)
                    for index, directory in enumerate(args.fixture_dirs)]
        if any(not directory.is_dir() or not list(directory.glob("*.cbz"))
               for directory in args.fixture_dirs):
            parser.error("each fixture directory must contain prepared CBZ archives")
    with tempfile.TemporaryDirectory(prefix="condor-performance-") as temporary:
        root = Path(temporary)
        for name, fixture_directory in selected:
            if fixture_directory is None:
                inputs = generate_workload(root / name, *WORKLOADS[name])
            else:
                inputs = sorted(fixture_directory.glob("*.cbz"))
            fixture_hashes[name] = [hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs]
            for trial in range(args.trials):
                variants = ["baseline", "optimized", "fork"]
                order.shuffle(variants)
                for variant in variants:
                    run = root / f"run-{name}-{trial}-{variant}"
                    run.mkdir()
                    scratch = run / "temporary"
                    scratch.mkdir()
                    for source in inputs:
                        shutil.copyfile(source, run / source.name)
                    metrics = run / "metrics.json"
                    source_root = baseline if variant == "baseline" else current
                    environment = dict(
                        os.environ, PYTHONPATH=str(source_root), TMPDIR=str(scratch),
                        TEMP=str(scratch), TMP=str(scratch),
                    )
                    command = [
                        sys.executable, str(Path(__file__).resolve()), "--child",
                        "--baseline-src", str(baseline), "--variant", variant,
                        "--run", str(run), "--metrics", str(metrics),
                    ]
                    measured = measure_child(command, scratch, environment, run)
                    measured.update({"workload": name, "variant": variant, "trial": trial + 1})
                    if metrics.exists():
                        measured.update(json.loads(metrics.read_text()))
                    measured.update(validate_outputs(inputs, run))
                    rows.append(measured)
                    print(
                        f"{name} {variant} trial={trial + 1}: "
                        f"{measured.get('conversion_wall_seconds', 'FAILED')}", flush=True,
                    )
                    shutil.rmtree(run)
            if fixture_directory is None:
                shutil.rmtree(root / name)
    report = {
        "schema_version": 1, "environment": environment_details(),
        "methodology": (
            "Fixed-seed fixtures, randomized variant order, fresh process per trial. "
            "One archive at a time; bounded hash helper thread permitted. Baseline/current "
            "verification, SHA-256 and fsync remain enabled. Every page receives decoded "
            "pixel and completeness validation outside conversion timing. Fork defaults "
            "can resize/recompress/omit formats; fidelity columns distinguish these cases. "
            "Shared host, warm filesystem caches, no pikepdf installed."
        ),
        "fixture_sha256": fixture_hashes,
        "reference_fork_sha256": hashlib.sha256(
            (Path(__file__).parent / "reference/fork.py").read_bytes()
        ).hexdigest(),
        "results": rows,
    }
    versions = {
        variant: sorted({r["environment"]["source_sha256"] for r in rows
                         if r["variant"] == variant and "environment" in r})
        for variant in ("baseline", "optimized")
    }
    report["measured_source_versions"] = versions
    report["source_versions_stable"] = all(len(hashes) == 1 for hashes in versions.values())
    write_json_exclusive(args.output, report)
    if not report["source_versions_stable"]:
        raise RuntimeError("source changed during comparison; raw evidence retained, no summary")
    write_summary(report, args.output.with_suffix(".md"))


if __name__ == "__main__":
    main()
