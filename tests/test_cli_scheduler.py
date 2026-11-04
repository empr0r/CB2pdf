import contextlib
import io
import json

from cb2pdf.cli import main
from cb2pdf.config import ConversionConfig, Quality, ResourceLimits
from cb2pdf.errors import OutputCollisionError
from cb2pdf.models import Status
from cb2pdf.scheduler import discover_jobs, run_batch

from .helpers import ArchiveTestCase


class ConfigurationTests(ArchiveTestCase):
    def test_invalid_configuration(self):
        for options in (
            {"max_size": (0, 10)}, {"dpi": float("nan")}, {"jpeg_quality": 80},
            {"upscale": True}, {"frames": "first"}, {"ordering": "random"},
            {"background": (256, 0, 0)}, {"quality": "small"},
            {"max_size": (1.5, 10)}, {"background": (0.5, 0, 0)},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                ConversionConfig(**options)
        with self.assertRaises(ValueError):
            ResourceLimits(max_pixels=0)
        with self.assertRaises(ValueError):
            ResourceLimits(max_member_bytes=1.5)

    def test_quality_defaults(self):
        self.assertIsNone(ConversionConfig().effective_max_size)
        self.assertEqual(ConversionConfig(quality=Quality.SMALL).effective_max_size, (1600, 1600))
        self.assertEqual(ConversionConfig(quality=Quality.BALANCED).effective_jpeg_quality, 90)


class SchedulerTests(ArchiveTestCase):
    def test_recursive_output_paths(self):
        chapter = self.root / "chapter"
        chapter.mkdir()
        original = self.archive()
        original.rename(chapter / original.name)
        output = self.root / "pdfs"
        jobs = discover_jobs([self.root], output, recursive=True)
        self.assertEqual(jobs[0].output, output / "chapter" / "comic.pdf")
        results = list(run_batch(jobs, ConversionConfig(), workers=2))
        self.assertTrue(all(r.ok for r in results))

    def test_duplicate_inputs_deduplicated(self):
        path = self.archive()
        self.assertEqual(len(discover_jobs([path, path], None)), 1)

    def test_same_stem_different_archives_collision(self):
        first = self.archive()
        second = self.archive(name="comic.cbr")
        with self.assertRaises(OutputCollisionError):
            discover_jobs([first, second], None)

    def test_casefold_output_collision(self):
        # Distinct source directories also exist on case-insensitive filesystems.
        (self.root / "a").mkdir()
        (self.root / "b").mkdir()
        first = self.archive(name="a/Comic.cbz")
        second = self.archive(name="b/comic.cbz")
        with self.assertRaises(OutputCollisionError):
            discover_jobs([first, second], self.root / "output")

    def test_fail_fast_reports_unstarted_archives(self):
        first = self.archive({"1.png": b"bad"}, name="a.cbz")
        second = self.archive(name="b.cbz")
        results = list(run_batch(discover_jobs(
            [first, second], None), ConversionConfig(), fail_fast=True))
        self.assertEqual([r.status for r in results], [Status.FAILED, Status.CANCELLED])
        self.assertFalse(second.with_suffix(".pdf").exists())

    def test_memory_budget_validation(self):
        jobs = discover_jobs([self.archive()], None)
        with self.assertRaises(ValueError):
            list(run_batch(jobs, ConversionConfig(), memory_budget_mb=1))
        with self.assertRaises(ValueError):
            list(run_batch(jobs, ConversionConfig(), workers=0))


class CliTests(ArchiveTestCase):
    def test_conversion_report_and_inspection(self):
        path = self.archive()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["inspect", str(path)]), 0)
        self.assertEqual(json.loads(output.getvalue())["format"], "zip")
        report = self.root / "results.json"
        self.assertEqual(main(["convert", str(path), "--quiet", "--report", str(report)]), 0)
        data = json.loads(report.read_text())
        self.assertEqual(data["successful"], 1)
        self.assertEqual(data["results"][0]["skipped_pages"], 0)

    def test_error_exit_codes(self):
        path = self.archive({"1.png": b"bad"})
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["convert", str(path), "--quiet"]), 1)
            self.assertEqual(main(["convert", str(path), "--dpi", "-1"]), 2)
            self.assertEqual(main(["convert", str(self.root / "missing")]), 2)

    def test_dry_run_and_report_protection(self):
        path = self.archive()
        report = self.root / "results.json"
        self.assertEqual(main(["convert", str(path), "--dry-run",
                         "--quiet", "--report", str(report)]), 0)
        self.assertFalse(report.exists())
        report.write_text("existing")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["convert", str(path), "--report", str(report)]), 2)
        self.assertEqual(report.read_text(), "existing")

    def test_logging_existing_files_protected(self):
        path = self.archive()
        original = path.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["convert", str(path), "--log-file", str(path)]), 2)
        self.assertEqual(path.read_bytes(), original)

    def test_log_cannot_occupy_future_pdf_destination(self):
        path = self.archive()
        with contextlib.redirect_stderr(io.StringIO()):
            code = main(["convert", str(path), "--log-file", str(path.with_suffix(".pdf"))])
        self.assertEqual(code, 2)
        self.assertFalse(path.with_suffix(".pdf").exists())

    def test_log_and_report_cannot_share_a_path(self):
        path = self.archive()
        sidecar = self.root / "result.json"
        with contextlib.redirect_stderr(io.StringIO()):
            code = main(["convert", str(path), "--log-file",
                        str(sidecar), "--report", str(sidecar)])
        self.assertEqual(code, 2)
        self.assertFalse(sidecar.exists())
