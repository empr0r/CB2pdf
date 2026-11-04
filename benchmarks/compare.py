"""Compare original, fork and current code in isolated processes on identical fixtures.

Run from the repository root: python benchmarks/compare.py --trials 3 --workers 1 2 4
Historical code is only executed against generated archives in owned temporary dirs.
"""

import argparse
import ast
import hashlib
import json
import os
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
from cb2pdf.config import ConversionConfig
from cb2pdf.models import ConversionJob
from cb2pdf.scheduler import run_batch

REFERENCE = Path(__file__).resolve().parent / "reference"
WORKLOADS = {
    "small-jpeg": (1, 12, (512, 768), ("JPEG",), False),
    "large-jpeg": (1, 24, (1600, 2400), ("JPEG",), False),
    "png-heavy": (1, 8, (1024, 1536), ("PNG",), False),
    "mixed-format": (1, 6, (800, 1200), ("JPEG", "PNG", "WEBP", "BMP", "GIF", "TIFF"), False),
    "high-resolution": (1, 4, (3000, 4500), ("JPEG",), False),
    "nested": (1, 12, (600, 900), ("PNG",), True),
    "many-small-volumes": (12, 4, (320, 480), ("JPEG",), False),
    "several-large-volumes": (3, 8, (1800, 2600), ("JPEG",), False),
}


def child(args):
    source = args.directory / "inputs"
    destination = args.directory / "outputs"
    destination.mkdir()
    paths = sorted(source.glob("*.cbz"))
    errors = 0
    namespace = {"__name__": "reference_benchmark", "__file__": str(destination / "cb2pdf.py")}
    if args.implementation != "redesigned":
        reference = REFERENCE / f"{args.implementation}.py"
        tree = ast.parse(reference.read_text())
        if args.implementation == "original":
            # Suppress only the import-time batch invocation. Run its batch function
            # below with identical worker counts and the artificial sleep disabled.
            tree.body = [node for node in tree.body if not (
                isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "process_files_in_batches"
            )]
        exec(compile(tree, str(reference), "exec"), namespace)
        for path in paths:
            shutil.copyfile(path, destination / path.name)
    _, cpu_start = process_usage()
    started = time.perf_counter()
    if args.implementation == "redesigned":
        results = list(run_batch([ConversionJob(p, destination / p.with_suffix(".pdf").name)
                       for p in paths], ConversionConfig(), args.workers))
        errors = sum(not r.ok for r in results)
    elif args.implementation == "original":
        namespace["process_files_in_batches"](batch_size=5, sleep_time=0, max_workers=args.workers)
    else:
        namespace["main"]()
    duration = time.perf_counter() - started
    rss, cpu_end = process_usage()
    cpu = cpu_end - cpu_start if cpu_start is not None and cpu_end is not None else None
    args.metrics.write_text(json.dumps({
        "conversion_wall_seconds": duration, "peak_rss_bytes": rss,
        "cpu_seconds": cpu, "cpu_percent": cpu / duration * 100 if cpu is not None else None,
        "reported_conversion_errors": errors if args.implementation == "redesigned" else None,
    }))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--workers", type=int, nargs="+", default=[1])
    parser.add_argument("--workloads", nargs="+", choices=list(WORKLOADS), default=list(WORKLOADS))
    parser.add_argument("--output", type=Path, default=Path("benchmarks/reports/comparison.json"))
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--implementation", choices=("original", "fork", "redesigned"))
    parser.add_argument("--metrics", type=Path)
    args = parser.parse_args()
    if args.child:
        args.workers = args.workers[0]
        child(args)
        return
    if args.trials < 1 or any(w < 1 for w in args.workers):
        parser.error("trials and workers must be positive")
    if args.output.exists() or args.output.with_suffix(".md").exists():
        parser.error("benchmark results already exist; choose another --output")
    rows = []
    with tempfile.TemporaryDirectory(prefix="condor-comparison-") as temporary:
        root = Path(temporary)
        for name in args.workloads:
            inputs = generate_workload(root / name, *WORKLOADS[name])
            for workers in args.workers:
                for implementation in ("original", "fork", "redesigned"):
                    if implementation == "fork" and workers != args.workers[0]:
                        continue
                    for trial in range(args.trials):
                        run = root / f"run-{name}-{implementation}-{workers}-{trial}"
                        (run / "inputs").mkdir(parents=True)
                        for path in inputs:
                            # Fixture setup is outside measured conversion.
                            shutil.copyfile(path, run / "inputs" / path.name)
                        temp = run / "temporary"
                        temp.mkdir()
                        metrics = run / "metrics.json"
                        environment = dict(os.environ, TMPDIR=str(
                            temp), TEMP=str(temp), TMP=str(temp))
                        command = [
                            sys.executable, str(Path(__file__).resolve()), "--child",
                            "--directory", str(run), "--implementation", implementation,
                            "--workers", str(workers), "--metrics", str(metrics),
                        ]
                        measured = measure_child(command, temp, environment, run / "outputs")
                        measured.update({
                            "workload": name, "implementation": implementation,
                            "workers": 1 if implementation == "fork" else workers,
                            "trial": trial + 1,
                        })
                        if metrics.exists():
                            measured.update(json.loads(metrics.read_text()))
                        measured.update(validate_outputs(inputs, run / "outputs"))
                        rows.append(measured)
                        duration = measured.get("conversion_wall_seconds", "FAILED")
                        print(
                            f"{name} {implementation} workers={measured['workers']} "
                            f"trial={trial+1}: {duration}", flush=True,
                        )
                        shutil.rmtree(run)
            shutil.rmtree(root / name)
    report = {
        "schema_version": 1, "environment": environment_details(),
        "references": {
            name: hashlib.sha256((REFERENCE / f"{name}.py").read_bytes()).hexdigest()
            for name in ("original", "fork")
        },
        "methodology": (
            "Fixed-seed textured images. Fresh process per trial. Original batch sleep=0; "
            "fork sequential; default quality policies differ. Conversion includes redesign "
            "verification/fsync. Fidelity is checked outside timing for every page. "
            "Temporary logical byte samples every 5 ms are lower bounds. CBR not measured: "
            "no representative comic RAR fixture."
        ),
        "results": rows,
    }
    write_json_exclusive(args.output, report)
    lines = [
        "# Measured comparison", "", report["methodology"], "",
        "| Workload | Implementation | Workers | Median seconds | Peak RSS MiB | "
        "Output MiB | Exact ordered pixels | Pages |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    keys = sorted({(r["workload"], r["implementation"], r["workers"]) for r in rows})
    for workload, implementation, workers in keys:
        group = [r for r in rows if (r["workload"], r["implementation"],
                                     r["workers"]) == (workload, implementation, workers)]
        durations = [r["conversion_wall_seconds"] for r in group if "conversion_wall_seconds" in r]
        if not durations:
            continue
        rss = max(r.get("peak_rss_bytes") or 0 for r in group) / 1024**2
        first = group[0]
        lines.append(
            f"| {workload} | {implementation} | {workers} | "
            f"{statistics.median(durations):.4f} | {rss:.1f} | "
            f"{first['output_bytes']/1024**2:.2f} | "
            f"{first['exact_pixel_pages_in_correct_order']}/{first['expected_pages']} | "
            f"{first['actual_pages']}/{first['expected_pages']} |"
        )
    with args.output.with_suffix(".md").open("x") as stream:
        stream.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
