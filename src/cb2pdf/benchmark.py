"""Reproducible generated workloads and fresh-process benchmark measurement.

The installed command benchmarks the current implementation. The repository runner
uses the same harness to compare the preserved upstream and fork snapshots.
"""

import argparse
import hashlib
import io
import json
import os
import platform
import random
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image
from pypdf import PdfReader
from pypdf.generic import DictionaryObject, StreamObject

from . import __version__
from .config import ConversionConfig
from .errors import ConversionError
from .models import ConversionJob
from .scheduler import run_batch
from .transactions import OutputTransaction


def generate_workload(
    directory: Path, volumes: int, pages: int, size: tuple[int, int],
    formats: tuple[str, ...] = ("JPEG",), nested: bool = False,
) -> list[Path]:
    """Use deterministic textured pixels, ordinary stored ZIPs, and single-frame images."""
    directory.mkdir(parents=True, exist_ok=True)
    inputs = []
    for volume in range(volumes):
        path = directory / f"volume-{volume:03d}.cbz"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            for page in range(pages):
                generator = random.Random(volume * 100_000 + page)
                # A repeated 64x64 noisy texture avoids both blank-page compression
                # artifacts and hundreds of MB of random fixture generation per trial.
                texture = Image.frombytes("RGB", (64, 64), generator.randbytes(64 * 64 * 3))
                with Image.new("RGB", size) as image:
                    for y in range(0, size[1], 64):
                        for x in range(0, size[0], 64):
                            image.paste(texture, (x, y))
                    buffer = io.BytesIO()
                    format = formats[page % len(formats)]
                    options = {"quality": 95, "subsampling": 0} if format == "JPEG" else {}
                    image.save(buffer, format=format, **options)
                texture.close()
                extension = {"JPEG": "jpg", "TIFF": "tif"}.get(format, format.lower())
                # Unpadded page numbers also exercise correctness of page ordering.
                prefix = f"Chapter {page // 10 + 1:02d}/" if nested else ""
                archive.writestr(f"{prefix}page{page + 1}.{extension}", buffer.getvalue())
        inputs.append(path)
    return inputs


def validate_outputs(inputs: list[Path], output_directory: Path) -> dict[str, Any]:
    """Outside timed conversion: check all pages, natural order and decoded pixels."""
    from .ordering import natural_key

    expected_count = actual_count = exact_pixels = exact_jpeg = jpeg_count = errors = 0
    output_bytes = 0
    for source in inputs:
        output = output_directory / source.with_suffix(".pdf").name
        with zipfile.ZipFile(source) as archive:
            names = sorted(archive.namelist(), key=natural_key)
            expected_count += len(names)
            if not output.exists():
                errors += 1
                continue
            output_bytes += output.stat().st_size
            reader = None
            stream = output.open("rb")
            try:
                reader = PdfReader(stream, strict=True)
                actual_count += len(reader.pages)
                if len(reader.pages) != len(names):
                    errors += 1
                for index, name in enumerate(names):
                    raw = archive.read(name)
                    is_jpeg = raw.startswith(b"\xff\xd8")
                    jpeg_count += is_jpeg
                    if index >= len(reader.pages):
                        continue
                    page = reader.pages[index]
                    resources = page["/Resources"].get_object()
                    if not isinstance(resources, DictionaryObject):
                        raise ValueError("invalid resource dictionary")
                    objects = resources["/XObject"].get_object()
                    if not isinstance(objects, DictionaryObject):
                        raise ValueError("invalid image dictionary")
                    obj = next(iter(objects.values())).get_object()
                    if not isinstance(obj, StreamObject):
                        raise ValueError("invalid image stream")
                    # pypdf's JPEG export API can re-encode even when the PDF's
                    # original stream is exact. Decode DCT streams directly here.
                    actual: Image.Image | None
                    if obj.get("/Filter") == "/DCTDecode":
                        actual = Image.open(io.BytesIO(obj._data))
                    else:
                        actual = page.images[0].image
                    if actual is None:
                        raise ValueError("PDF image could not be decoded")
                    with Image.open(io.BytesIO(raw)) as expected:
                        with actual:
                            if actual.size == expected.size:
                                with (
                                    actual.convert("RGBA") as left,
                                    expected.convert("RGBA") as right,
                                ):
                                    expected_digest = hashlib.sha256(right.tobytes()).digest()
                                    actual_digest = hashlib.sha256(left.tobytes()).digest()
                                    exact_pixels += actual_digest == expected_digest
                    if is_jpeg:
                        exact_jpeg += obj._data == raw
            except Exception:
                errors += 1
            finally:
                if reader is not None:
                    reader.close()
                stream.close()
    return {
        "expected_pages": expected_count, "actual_pages": actual_count,
        "exact_pixel_pages_in_correct_order": exact_pixels,
        "jpeg_pages": jpeg_count, "exact_jpeg_streams": exact_jpeg,
        "validation_errors": errors, "output_bytes": output_bytes,
    }


def _temporary_bytes(directory: Path) -> int:
    total = 0
    for path in directory.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except FileNotFoundError:
            pass
    return total


def measure_child(
    command: list[str], temporary_directory: Path, environment: dict[str, str],
    output_directory: Path | None = None,
) -> dict[str, Any]:
    """Sample temporary logical bytes every 5 ms (a lower bound, not exact I/O volume)."""
    stopped = threading.Event()
    peak = [0]

    def sample() -> None:
        while not stopped.is_set():
            size = _temporary_bytes(temporary_directory)
            if output_directory is not None:
                for path in output_directory.rglob("*.cb2pdf-part"):
                    try:
                        size += path.stat().st_size
                    except FileNotFoundError:
                        pass
            peak[0] = max(peak[0], size)
            stopped.wait(0.005)

    sampler = threading.Thread(target=sample, daemon=True)
    started = time.perf_counter()
    sampler.start()
    try:
        process = subprocess.run(command, env=environment,
                                 capture_output=True, text=True, check=False)
    finally:
        stopped.set()
        sampler.join()
    return {
        "process_wall_seconds": time.perf_counter() - started,
        "peak_temporary_bytes_sampled": peak[0], "returncode": process.returncode,
        "stderr": process.stderr[-4000:],
    }


def process_usage() -> tuple[int | None, float | None]:
    try:
        import resource
    except ImportError:
        return None, None
    usage = resource.getrusage(resource.RUSAGE_SELF)
    multiplier = 1 if sys.platform == "darwin" else 1024
    peak_rss = int(usage.ru_maxrss * multiplier)
    if sys.platform.startswith("linux"):
        # getrusage's high-water mark can include memory inherited across fork/exec.
        # Linux resets this process's /proc VmHWM on exec; measure the worker itself.
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                peak_rss = int(line.split()[1]) * 1024
                break
    return peak_rss, usage.ru_utime + usage.ru_stime


def environment_details() -> dict[str, Any]:
    import img2pdf
    import PIL
    import pypdf

    cpu_model = platform.processor()
    memory_total = None
    if sys.platform.startswith("linux"):
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                memory_total = int(line.split()[1]) * 1024
                break
    source_hash = hashlib.sha256()
    for source in sorted(Path(__file__).parent.glob("*.py")):
        source_hash.update(source.name.encode())
        source_hash.update(source.read_bytes())
    return {
        "platform": platform.platform(), "machine": platform.machine(),
        "processor": platform.processor(), "logical_cpus": os.cpu_count(),
        "python": sys.version, "cb2pdf": __version__, "pillow": PIL.__version__,
        "img2pdf": img2pdf.__version__, "pypdf": pypdf.__version__,
        "cpu_model": cpu_model, "memory_total_bytes": memory_total,
        "source_sha256": source_hash.hexdigest(),
        "memory_note": (
            "Linux: /proc/self/status VmHWM after conversion, since exec, including imports. "
            "Other POSIX: getrusage ru_maxrss (may include inherited high-water mark). "
            "Resource metrics unavailable on Windows."
        ),
    }


def write_json_exclusive(path: Path, data: dict[str, Any]) -> None:
    with OutputTransaction(path) as transaction:
        assert transaction.stream is not None
        transaction.stream.write(json.dumps(data, indent=2).encode())
        transaction.finish_writing()
        transaction.commit()


def run_benchmark(output: Path, trials: int = 3, workers: int = 1, quick: bool = False) -> None:
    """Benchmark current code in fresh child interpreters; never process user comics."""
    if trials < 1 or workers < 1:
        raise ValueError("trials and workers must be positive")
    if output.exists():
        raise FileExistsError(f"benchmark output already exists: {output}")
    results = []
    with tempfile.TemporaryDirectory(prefix="cb2pdf-benchmark-") as temporary:
        root = Path(temporary)
        inputs = generate_workload(root / "inputs", 2 if quick else 8,
                                   3 if quick else 12, (320, 480) if quick else (1000, 1500))
        for trial in range(trials):
            trial_directory = root / f"trial-{trial}"
            trial_directory.mkdir()
            temporary_data = trial_directory / "temporary"
            temporary_data.mkdir()
            environment = dict(os.environ, TMPDIR=str(temporary_data),
                               TEMP=str(temporary_data), TMP=str(temporary_data))
            metrics = trial_directory / "metrics.json"
            command = [
                sys.executable, "-m", "cb2pdf.benchmark", "--worker",
                "--input", str(root / "inputs"), "--output", str(trial_directory),
                "--workers", str(workers), "--metrics", str(metrics),
            ]
            measured = measure_child(command, temporary_data, environment, trial_directory)
            if measured["returncode"] or not metrics.exists():
                raise ConversionError(f"benchmark worker failed: {measured['stderr']}")
            measured.update(json.loads(metrics.read_text()))
            measured.update(validate_outputs(inputs, trial_directory))
            measured["trial"] = trial + 1
            results.append(measured)
    write_json_exclusive(output, {"schema_version": 1, "environment": environment_details(
    ), "workers": workers, "quick": quick, "trials": results})


def worker(input_directory: Path, output_directory: Path, workers: int, metrics: Path) -> None:
    jobs = [ConversionJob(p, output_directory / p.with_suffix(".pdf").name)
            for p in sorted(input_directory.glob("*.cbz"))]
    _, cpu_started = process_usage()
    started = time.perf_counter()
    results = list(run_batch(jobs, ConversionConfig(), workers))
    duration = time.perf_counter() - started
    rss, cpu_finished = process_usage()
    cpu_seconds = None
    if cpu_started is not None and cpu_finished is not None:
        cpu_seconds = cpu_finished - cpu_started
    metrics.write_text(json.dumps({
        "conversion_wall_seconds": duration, "peak_rss_bytes": rss,
        "cpu_seconds": cpu_seconds,
        "cpu_percent": cpu_seconds / duration * 100 if cpu_seconds is not None else None,
        "conversion_errors": sum(not result.ok for result in results),
    }))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--metrics", type=Path, required=True)
    arguments = parser.parse_args()
    worker(arguments.input, arguments.output, arguments.workers, arguments.metrics)
