from cb2pdf.benchmark import generate_workload, run_benchmark, validate_outputs
from cb2pdf.converter import convert

from .helpers import ArchiveTestCase


class BenchmarkTests(ArchiveTestCase):
    def test_exact_jpeg_validation_avoids_export_recompression(self):
        inputs = generate_workload(self.root / "inputs", 1, 2, (64, 96))
        output = self.root / "output"
        output.mkdir()
        self.assertTrue(convert(inputs[0], output / "volume-000.pdf").ok)
        result = validate_outputs(inputs, output)
        self.assertEqual(result["exact_pixel_pages_in_correct_order"], 2)
        self.assertEqual(result["exact_jpeg_streams"], 2)
        self.assertEqual(result["validation_errors"], 0)

    def test_benchmark_rejects_invalid_trials_and_existing_output(self):
        with self.assertRaises(ValueError):
            run_benchmark(self.root / "report.json", trials=0)
        report = self.root / "report.json"
        report.write_text("existing")
        with self.assertRaises(FileExistsError):
            run_benchmark(report, trials=1, quick=True)
        self.assertEqual(report.read_text(), "existing")
