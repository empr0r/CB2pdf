"""Test an installed wheel outside the source tree and retain machine-readable evidence.

Install the wheel and development dependencies in the chosen interpreter first.
This command never installs software, downloads data, pushes Git refs or publishes.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


def probe(artifact: Path, report: Path, require_rar: bool) -> int:
    """Verify installed provenance, run staged tests, and exercise the installed CLI."""
    import cb2pdf

    package = Path(cb2pdf.__file__).resolve().parent
    if not package.is_relative_to(Path(sys.prefix).resolve()):
        raise RuntimeError(f"expected an isolated installed package, found {package}")
    if cb2pdf.__version__ != importlib.metadata.version("cb2pdf"):
        raise RuntimeError("package and distribution versions differ")
    with zipfile.ZipFile(artifact) as wheel:
        entries = [name for name in wheel.namelist() if name.startswith("cb2pdf/")]
        if not entries:
            raise RuntimeError("wheel does not contain the cb2pdf package")
        for name in entries:
            installed = package.parent / name
            if not installed.is_file() or installed.read_bytes() != wheel.read(name):
                raise RuntimeError(f"installed file differs from wheel: {name}")
    if require_rar:
        import rarfile

        rarfile.tool_setup()
    suite = unittest.defaultTestLoader.discover("tests", top_level_dir=str(Path.cwd()))
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    smoke = Path("installed-smoke.json")
    commands = [
        [sys.executable, "-m", "cb2pdf", "--version"],
        [sys.executable, "-m", "cb2pdf", "benchmark", "--quick", "--trials", "1",
         "--output", str(smoke)],
    ]
    cli = []
    for command in commands:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
        cli.append({"arguments": command[2:], "returncode": completed.returncode,
                    "stdout": completed.stdout, "stderr": completed.stderr})
    metrics = json.loads(smoke.read_text()) if smoke.exists() else None
    smoke_ok = bool(metrics) and all(
        trial["returncode"] == trial["conversion_errors"] == trial["validation_errors"] == 0
        and trial["actual_pages"] == trial["expected_pages"]
        == trial["exact_pixel_pages_in_correct_order"]
        and trial["jpeg_pages"] == trial["exact_jpeg_streams"]
        for trial in metrics["trials"]
    )
    success = result.wasSuccessful() and all(c["returncode"] == 0 for c in cli) and smoke_ok
    dependencies = {}
    for name in ("cb2pdf", "Pillow", "img2pdf", "pypdf", "pikepdf", "rarfile"):
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = None
    record = {
        "schema_version": 1, "success": success, "python": sys.version,
        "platform": platform.platform(), "installed_package": str(package),
        "artifact": artifact.name,
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "verified_wheel_entries": len(entries), "dependencies": dependencies,
        "tests_run": result.testsRun,
        "failures": [case.id() for case, _ in result.failures],
        "errors": [case.id() for case, _ in result.errors],
        "skipped": [{"test": case.id(), "reason": reason} for case, reason in result.skipped],
        "backends": {name: shutil.which(name) for name in ("unrar", "unar", "bsdtar", "7z")},
        "cli": cli, "smoke": metrics,
    }
    with report.open("x") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    return 0 if success else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--require-rar", action="store_true")
    parser.add_argument("--probe", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    if args.probe:
        return probe(artifact, args.report, args.require_rar)
    destination = args.report.resolve()
    log = destination.with_suffix(".log")
    if destination.exists() or log.exists():
        parser.error("choose new report and log paths")
    destination.parent.mkdir(parents=True, exist_ok=True)
    repository = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="cb2pdf-release-") as temporary:
        stage = Path(temporary)
        shutil.copytree(repository / "tests", stage / "tests",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (stage / "benchmarks").mkdir()
        for source in (repository / "benchmarks").glob("*.py"):
            shutil.copyfile(source, stage / "benchmarks" / source.name)
        command = [sys.executable, str(Path(__file__).resolve()), "--probe",
                   "--artifact", str(artifact), "--report", str(destination)]
        if args.require_rar:
            command.append("--require-rar")
        environment = {key: value for key, value in os.environ.items()
                       if key not in ("PYTHONPATH", "PYTHONHOME")}
        completed = subprocess.run(command, cwd=stage, env=environment,
                                   capture_output=True, text=True, timeout=600)
        with log.open("x") as stream:
            stream.write(completed.stdout + completed.stderr)
        if not destination.exists():
            with destination.open("x") as stream:
                json.dump({"schema_version": 1, "success": False,
                           "returncode": completed.returncode,
                           "error": "probe failed before writing metrics; see adjacent log"},
                          stream)
        print(f"{'PASS' if completed.returncode == 0 else 'FAIL'}: {destination}")
        return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
