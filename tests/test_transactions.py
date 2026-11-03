import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from cb2pdf.config import ConversionConfig
from cb2pdf.converter import convert
from cb2pdf.models import Status
from cb2pdf.pdf import verify_pdf, write_pdf
from cb2pdf.transactions import OutputTransaction

from .helpers import ArchiveTestCase, image_bytes


class TransactionTests(ArchiveTestCase):
    def test_existing_output_never_overwritten(self):
        path = self.archive()
        output = path.with_suffix(".pdf")
        output.write_bytes(b"precious existing output")
        result = convert(path, config=ConversionConfig(move_original=self.root / "old"))
        self.assertEqual(result.error_type, "OutputCollisionError")
        self.assertEqual(output.read_bytes(), b"precious existing output")
        self.assertTrue(path.exists())
        self.assert_clean()

    def test_failed_conversion_never_archives(self):
        path = self.archive({"1.png": b"broken"})
        result = convert(path, config=ConversionConfig(move_original=self.root / "old"))
        self.assertFalse(result.ok)
        self.assertTrue(path.exists())
        self.assertFalse((self.root / "old").exists())

    def test_original_moved_only_after_commit(self):
        path = self.archive()
        original = path.read_bytes()
        result = convert(path, config=ConversionConfig(move_original=self.root / "old"))
        self.assertTrue(result.ok, result.error)
        self.assertTrue(result.committed and result.verified)
        self.assertFalse(path.exists())
        self.assertFalse(result.source_retained)
        self.assertEqual((self.root / "old" / path.name).read_bytes(), original)
        self.assert_clean()

    def test_archive_destination_collision_is_partial_success(self):
        path = self.archive()
        destination = self.root / "old" / path.name
        destination.parent.mkdir()
        destination.write_bytes(b"previous archive")
        result = convert(path, config=ConversionConfig(move_original=destination.parent))
        self.assertEqual(result.status, Status.ARCHIVAL_FAILED)
        self.assertTrue(result.committed and result.verified)
        self.assertTrue(path.exists())
        self.assertTrue(path.with_suffix(".pdf").exists())
        self.assertEqual(destination.read_bytes(), b"previous archive")

    def test_explicit_overwrite(self):
        path = self.archive()
        output = path.with_suffix(".pdf")
        output.write_bytes(b"old")
        self.assertTrue(convert(path, config=ConversionConfig(overwrite=True)).ok)
        self.assertTrue(output.read_bytes().startswith(b"%PDF-"))

    def test_failed_overwrite_preserves_previous_pdf(self):
        path = self.archive({"1.png": b"bad"})
        output = path.with_suffix(".pdf")
        output.write_bytes(b"existing")
        self.assertFalse(convert(path, config=ConversionConfig(overwrite=True)).ok)
        self.assertEqual(output.read_bytes(), b"existing")

    def test_same_input_output_refused_even_with_overwrite(self):
        path = self.archive()
        original = path.read_bytes()
        result = convert(path, path, ConversionConfig(overwrite=True))
        self.assertEqual(result.error_type, "OutputCollisionError")
        self.assertEqual(path.read_bytes(), original)

    def test_two_concurrent_conversions_one_exclusive_winner(self):
        path = self.archive()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: convert(path), range(2)))
        self.assertEqual(sum(r.ok for r in results), 1)
        self.assertEqual([r.error_type for r in results if not r.ok], ["OutputCollisionError"])
        self.assertTrue(path.exists())
        self.assert_clean()

    def test_unique_temporary_names_and_owned_cleanup(self):
        destination = self.root / "comic.pdf"
        unrelated = self.root / ".cb2pdf-unrelated.cb2pdf-part"
        unrelated.write_bytes(b"keep")
        with OutputTransaction(destination) as first, OutputTransaction(destination) as second:
            self.assertNotEqual(first.temporary, second.temporary)
            temporary = first.temporary
        self.assertFalse(temporary.exists())
        self.assertEqual(unrelated.read_bytes(), b"keep")

    def test_write_failure_cleans_temporary(self):
        path = self.archive()
        with patch("cb2pdf.converter.write_pdf", side_effect=OSError("injected disk full")):
            result = convert(path)
        self.assertFalse(result.ok)
        self.assertTrue(path.exists())
        self.assertFalse(path.with_suffix(".pdf").exists())
        self.assert_clean()

    def test_cleanup_is_attempted_even_if_buffer_close_fails(self):
        destination = self.root / "comic.pdf"
        transaction = OutputTransaction(destination)
        transaction.__enter__()
        temporary = transaction.temporary
        original_stream = transaction.stream
        original_stream.close()
        with patch.object(original_stream, "close", side_effect=OSError("close failed")):
            with self.assertRaises(OSError):
                transaction.__exit__(None, None, None)
        self.assertFalse(temporary.exists())
        self.assertFalse(destination.exists())

    def test_structure_corruption_prevents_commit(self):
        path = self.archive()

        def corrupt_then_verify(temporary, pages):
            temporary.write_bytes(b"broken PDF")
            return verify_pdf(temporary, pages)

        with patch("cb2pdf.converter.verify_pdf", side_effect=corrupt_then_verify):
            result = convert(path)
        self.assertEqual(result.error_type, "PdfVerificationError")
        self.assertTrue(path.exists())
        self.assertFalse(path.with_suffix(".pdf").exists())
        self.assert_clean()

    def test_missing_pdf_page_prevents_commit(self):
        path = self.archive({"1.png": image_bytes(), "2.png": image_bytes()})

        def omit_page(pages, stream, config):
            write_pdf(pages[:1], stream, config)

        with patch("cb2pdf.converter.write_pdf", side_effect=omit_page):
            result = convert(path)
        self.assertEqual(result.error_type, "PdfVerificationError")
        self.assertTrue(path.exists())
        self.assertFalse(path.with_suffix(".pdf").exists())
        self.assert_clean()

    def test_source_mutation_detected_before_commit(self):
        path = self.archive()

        def mutate_source(temporary, pages):
            verification = verify_pdf(temporary, pages)
            with path.open("ab") as stream:
                stream.write(b"changed")
            return verification

        with patch("cb2pdf.converter.verify_pdf", side_effect=mutate_source):
            result = convert(path)
        self.assertFalse(result.committed)
        self.assertTrue(path.exists())
        self.assertFalse(path.with_suffix(".pdf").exists())

    def test_reordered_pages_of_equal_dimensions_prevent_commit(self):
        path = self.archive({
            "1.jpg": image_bytes("JPEG", color=(255, 0, 0)),
            "2.jpg": image_bytes("JPEG", color=(0, 0, 255)),
        })

        def reverse_pages(pages, stream, config):
            write_pdf(list(reversed(pages)), stream, config)

        with patch("cb2pdf.converter.write_pdf", side_effect=reverse_pages):
            result = convert(path)
        self.assertEqual(result.error_type, "PdfVerificationError")
        self.assertTrue(path.exists())
        self.assertFalse(path.with_suffix(".pdf").exists())

    def test_keyboard_interrupt_cleans_without_claiming_success(self):
        path = self.archive()
        with patch("cb2pdf.converter.write_pdf", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                convert(path)
        self.assertTrue(path.exists())
        self.assertFalse(path.with_suffix(".pdf").exists())
        self.assert_clean()

    def test_cancelled_before_start(self):
        path = self.archive()
        cancel = threading.Event()
        cancel.set()
        result = convert(path, cancel=cancel)
        self.assertEqual(result.status, Status.CANCELLED)
        self.assertTrue(path.exists())

    def test_directory_sync_failure_reports_committed_output(self):
        path = self.archive()
        with patch("cb2pdf.transactions.sync_directory", side_effect=OSError("sync failed")):
            result = convert(path)
        self.assertEqual(result.status, Status.COMMIT_INCOMPLETE)
        self.assertTrue(result.committed)
        self.assertTrue(path.exists())
        self.assertTrue(path.with_suffix(".pdf").exists())
        self.assert_clean()

    def test_dry_run_no_persistent_writes_or_source_move(self):
        path = self.archive()
        destination = self.root / "not-created" / "comic.pdf"
        result = convert(path, destination, ConversionConfig(
            dry_run=True, move_original=self.root / "old"))
        self.assertEqual(result.status, Status.DRY_RUN)
        self.assertFalse(destination.parent.exists())
        self.assertFalse((self.root / "old").exists())
        self.assertTrue(path.exists())
