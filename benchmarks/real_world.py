"""Build private CBZ fixtures from image-only PDFs and measure the current converter.

This tests real page content, not the original comic archives. Source PDFs stay read-only.
Fixtures and converted PDFs stay in the ignored work directory; only metrics are reported.
"""

import argparse
import hashlib
import io
import json
import logging
import os
import sys
import zipfile
from pathlib import Path
from collections import Counter

from PIL import Image
from pypdf import PageObject, PdfReader
from pypdf.generic import StreamObject

from cb2pdf.benchmark import (
    environment_details, measure_child, validate_outputs, write_json_exclusive,
)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def export_image(image: StreamObject, page: PageObject) -> Image.Image:
    """Preserve indexed ASCIIHex samples; pypdf's generic image export can lose palettes."""
    color_space = image.get("/ColorSpace")
    if (
        image.get("/Filter") == "/ASCIIHexDecode"
        and isinstance(color_space, list) and color_space[0] == "/Indexed"
        and color_space[1] == "/DeviceRGB"
    ):
        bits = int(image["/BitsPerComponent"])
        width, height = int(image["/Width"]), int(image["/Height"])
        raw_mode = "P" if bits == 8 else f"P;{bits}"
        decoded = Image.frombytes(
            "P", (width, height), image.get_data(), "raw", raw_mode, 0, 1,
        )
        palette = color_space[3].get_object()
        palette_data = palette.original_bytes if hasattr(
            palette, "original_bytes") else palette.get_data()
        decoded.putpalette(palette_data)
        return decoded
    if image.get("/Filter") == "/JPXDecode":
        return Image.open(io.BytesIO(image._data))
    decoded = page.images[0].image
    if decoded is None:
        raise ValueError("cannot decode PDF image")
    return decoded


class WarningCounter(logging.Handler):
    """Retain parser-recovery diagnostics without hundreds of duplicate console lines."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.messages: Counter[str] = Counter()

    def emit(self, record: logging.LogRecord) -> None:
        self.messages[record.getMessage()] += 1


def repack_pdf(source: Path, destination: Path) -> dict:
    direct = normalized = 0
    warnings = WarningCounter()
    parser_logger = logging.getLogger("pypdf")
    previous_propagation = parser_logger.propagate
    parser_logger.addHandler(warnings)
    parser_logger.propagate = False
    with source.open("rb") as stream, zipfile.ZipFile(destination, "x") as archive:
        reader = PdfReader(stream)
        try:
            count = len(reader.pages)
            for index, page in enumerate(reader.pages):
                objects = page["/Resources"]["/XObject"]
                images = [ref.get_object() for ref in objects.values()]
                images = [obj for obj in images if obj.get("/Subtype") == "/Image"]
                if len(images) != 1:
                    raise ValueError("real fixture import requires one image per PDF page")
                image = images[0]
                if image.get("/Filter") == "/DCTDecode" and not image.get("/SMask"):
                    raw, extension = image._data, "jpg"
                    direct += 1
                else:
                    decoded = export_image(image, page)
                    with decoded:
                        buffer = io.BytesIO()
                        decoded.save(buffer, "PNG")
                        raw, extension = buffer.getvalue(), "png"
                    normalized += 1
                archive.writestr(f"page{index + 1:05d}.{extension}", raw)
        finally:
            reader.close()
            parser_logger.removeHandler(warnings)
            parser_logger.propagate = previous_propagation
    return {
        "pages": count, "jpeg_streams_repacked_exactly": direct,
        "pdf_images_exported_to_lossless_png": normalized,
        "source_pdf_parser_warnings": dict(warnings.messages),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdfs", type=Path, nargs="+")
    parser.add_argument("--work", type=Path, default=Path("benchmarks/work/real"))
    parser.add_argument("--output", type=Path, default=Path("benchmarks/reports/real-world.json"))
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()
    if args.trials < 1 or args.output.exists() or args.work.exists():
        parser.error("positive trials and new work/report paths are required")
    if any(not p.is_file() for p in args.pdfs):
        parser.error("every source must be an existing PDF")
    args.work.mkdir(parents=True)
    results = []
    sources = []
    for index, pdf in enumerate(args.pdfs):
        before = digest(pdf)
        fixture_directory = args.work / f"volume-{index}"
        fixture_directory.mkdir()
        fixture = fixture_directory / "volume-000.cbz"
        preparation = repack_pdf(pdf, fixture)
        sources.append({
            "label": f"real-volume-{index + 1}", "source_bytes": pdf.stat().st_size,
            "source_sha256_before": before, "source_sha256_after": digest(pdf),
            "fixture_bytes": fixture.stat().st_size, **preparation,
        })
        print(f"prepared real-volume-{index + 1}: {preparation['pages']} pages", flush=True)
        for trial in range(args.trials):
            trial_directory = args.work / f"volume-{index}-trial-{trial}"
            trial_directory.mkdir()
            temporary = trial_directory / "temporary"
            temporary.mkdir()
            metrics = trial_directory / "metrics.json"
            command = [
                sys.executable, "-m", "cb2pdf.benchmark", "--worker",
                "--input", str(fixture_directory), "--output", str(trial_directory),
                "--workers", "1", "--metrics", str(metrics),
            ]
            environment = dict(os.environ, TMPDIR=str(temporary.resolve()),
                               TEMP=str(temporary.resolve()), TMP=str(temporary.resolve()))
            measured = measure_child(command, temporary, environment, trial_directory)
            if metrics.exists():
                measured.update(json.loads(metrics.read_text()))
            measured.update(validate_outputs([fixture], trial_directory))
            measured.update({"label": f"real-volume-{index + 1}", "trial": trial + 1})
            results.append(measured)
            print(f"real-volume-{index + 1} trial {trial + 1}: complete", flush=True)
    write_json_exclusive(args.output, {
        "schema_version": 1, "environment": environment_details(),
        "limitation": "Repacked image content from user PDFs, not original archive files. "
                      "Document text/overlays/layout metadata are outside this test.",
        "sources": sources, "results": results,
    })


if __name__ == "__main__":
    main()
