"""Behavioral regressions for optimized paths, including uncommon PNG metadata positions."""

import hashlib
import io
import random
import struct
import threading
import zlib
import gc
import weakref
from unittest.mock import patch

from PIL import Image, JpegImagePlugin, PngImagePlugin
from pypdf import PdfReader

from cb2pdf.converter import convert
from cb2pdf.config import ConversionConfig, ResourceLimits
from cb2pdf.digests import DigestPipeline, image_stream_digest
from cb2pdf.errors import CancelledError, ImageDecodeError
from cb2pdf.png import inspect_png_chunks
from cb2pdf.pdf import write_pdf

from .helpers import ArchiveTestCase, image_bytes, page_image


def move_chunk_after_data(data: bytes, kind: bytes) -> bytes:
    offset = 8
    chunks = []
    moved = []
    while offset < len(data):
        length = int.from_bytes(data[offset:offset + 4], "big")
        chunk = data[offset:offset + length + 12]
        if chunk[4:8] == kind:
            moved.append(chunk)
        else:
            chunks.append(chunk)
        offset += length + 12
    return data[:8] + b"".join(chunks[:-1] + moved + chunks[-1:])


def replace_idat(data: bytes, payload: bytes) -> bytes:
    start = data.index(b"IDAT") - 4
    length = int.from_bytes(data[start:start + 4], "big")
    body = b"IDAT" + payload
    chunk = len(payload).to_bytes(4, "big") + body + zlib.crc32(body).to_bytes(4, "big")
    return data[:start] + chunk + data[start + length + 12:]


class PngMetadataTests(ArchiveTestCase):
    def test_opaque_png_does_not_decode_pixels(self):
        path = self.archive()
        with patch.object(
            PngImagePlugin.PngImageFile, "load", side_effect=AssertionError("decoded"),
        ):
            result = convert(path)
        self.assertTrue(result.ok, result.error)
        self.assertEqual(page_image(path.with_suffix(".pdf")).size, (64, 96))

    def test_late_exif_rotation_without_pixel_decode(self):
        exif = Image.Exif()
        exif[274] = 6
        data = move_chunk_after_data(image_bytes(exif=exif), b"eXIf")
        path = self.archive({"page.png": data})
        with patch.object(
            PngImagePlugin.PngImageFile, "load", side_effect=AssertionError("decoded"),
        ):
            result = convert(path)
        self.assertTrue(result.ok, result.error)
        self.assertEqual(PdfReader(path.with_suffix(".pdf")).pages[0].rotation, 90)

    def test_late_xmp_orientation(self):
        info = PngImagePlugin.PngInfo()
        info.add_text("XML:com.adobe.xmp", '<tiff:Orientation="8">')
        data = move_chunk_after_data(image_bytes(pnginfo=info), b"tEXt")
        path = self.archive({"page.png": data})
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        self.assertEqual(PdfReader(path.with_suffix(".pdf")).pages[0].rotation, 270)

    def test_invalid_late_orientation_is_rejected(self):
        exif = Image.Exif()
        exif[274] = 0
        path = self.archive({"page.png": move_chunk_after_data(image_bytes(exif=exif), b"eXIf")})
        result = convert(path)
        self.assertEqual(result.error_type, "ImageDecodeError")
        self.assertFalse(path.with_suffix(".pdf").exists())

    def test_chunk_crc_remains_enforced(self):
        data = bytearray(image_bytes())
        offset = data.index(b"IDAT") + 4
        data[offset] ^= 1
        path = self.archive({"page.png": bytes(data)})
        result = convert(path)
        self.assertEqual(result.error_type, "ImageDecodeError")
        self.assertFalse(path.with_suffix(".pdf").exists())

    def test_invalid_chunk_extent_is_bounded(self):
        data = bytearray(image_bytes())
        offset = data.index(b"IDAT") - 4
        struct.pack_into(">I", data, offset, 0x7FFFFFFF)
        path = self.archive({"page.png": bytes(data)})
        self.assertFalse(convert(path).ok)

    def test_apng_frame_controls_are_not_overwritten(self):
        buffer = io.BytesIO()
        images = [Image.new("RGBA", (30, 40), color) for color in ("red", "blue", "green")]
        images[0].save(buffer, "PNG", save_all=True, append_images=images[1:], duration=100)
        for image in images:
            image.close()
        path = self.archive({"animated.png": buffer.getvalue()})
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        self.assertEqual(len(result.pages), 3)
        self.assertEqual(page_image(path.with_suffix(".pdf"), 0).convert(
            "RGB").getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(page_image(path.with_suffix(".pdf"), 1).convert(
            "RGB").getpixel((0, 0)), (0, 0, 255))

    def test_chunk_scan_cancellation(self):
        cancelled = threading.Event()
        cancelled.set()
        data = image_bytes()
        with self.assertRaises(CancelledError):
            inspect_png_chunks(io.BytesIO(data), len(data), cancelled)

    def test_invalid_late_color_and_layout_metadata_is_not_silently_dropped(self):
        from PIL import ImageCms

        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        cases = [
            (b"iCCP", image_bytes(icc_profile=profile)),
            (b"tRNS", image_bytes(transparency=(30, 80, 150))),
            (b"pHYs", image_bytes(dpi=(300, 300))),
        ]
        for kind, data in cases:
            with self.subTest(kind=kind):
                path = self.archive({"page.png": move_chunk_after_data(data, kind)})
                result = convert(path)
                self.assertEqual(result.error_type, "ImageDecodeError")
                self.assertTrue(path.exists())
                self.assertFalse(path.with_suffix(".pdf").exists())

    def test_bad_deflate_checksum_with_valid_chunk_crc_is_rejected(self):
        data = image_bytes()
        start = data.index(b"IDAT")
        length = int.from_bytes(data[start - 4:start], "big")
        payload = bytearray(data[start + 4:start + 4 + length])
        payload[-1] ^= 1
        result = convert(self.archive({"page.png": replace_idat(data, bytes(payload))}))
        self.assertEqual(result.error_type, "ImageDecodeError")
        self.assertFalse(self.root.joinpath("comic.pdf").exists())

    def test_truncated_scanlines_with_valid_checksums_are_rejected(self):
        data = replace_idat(image_bytes(), zlib.compress(bytes(193 * 96 - 1)))
        result = convert(self.archive({"page.png": data}))
        self.assertEqual(result.error_type, "ImageDecodeError")

    def test_invalid_filter_with_valid_checksums_is_rejected(self):
        raw = b"\x05" + bytes(193 * 96 - 1)
        data = replace_idat(image_bytes(), zlib.compress(raw))
        result = convert(self.archive({"page.png": data}))
        self.assertEqual(result.error_type, "ImageDecodeError")

    def test_png_inner_decompression_bomb_is_bounded_by_dimensions(self):
        data = replace_idat(image_bytes(), zlib.compress(bytes(1024**2)))
        result = convert(self.archive({"page.png": data}))
        self.assertEqual(result.error_type, "ResourceLimitError")
        self.assertFalse(self.root.joinpath("comic.pdf").exists())

    def test_single_frame_apng_uses_frame_normalization(self):
        # Pillow optimizes a one-frame save into plain PNG; build the two
        # animation-control chunks explicitly while retaining its valid IDAT.
        data = image_bytes(size=(30, 40), color=(255, 0, 0))

        def chunk(kind, payload):
            body = kind + payload
            return len(payload).to_bytes(4, "big") + body + zlib.crc32(body).to_bytes(4, "big")

        animation = chunk(b"acTL", struct.pack(">II", 1, 0))
        frame = chunk(b"fcTL", struct.pack(">IIIIIHHBB", 0, 30, 40, 0, 0, 100, 1000, 0, 0))
        data = data[:33] + animation + frame + data[33:]
        result = convert(self.archive({"one-frame.png": data}))
        self.assertTrue(result.ok, result.error)
        self.assertEqual(len(result.pages), 1)
        self.assertEqual(result.normalized_pages, 1)

    def test_plain_png_loop_text_does_not_trigger_animation_normalization(self):
        info = PngImagePlugin.PngInfo()
        info.add_text("loop", "0")
        path = self.archive({"page.png": image_bytes(pnginfo=info)})
        with patch.object(
            PngImagePlugin.PngImageFile, "load", side_effect=AssertionError("decoded"),
        ):
            result = convert(path)
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.normalized_pages, 0)


class DigestTests(ArchiveTestCase):
    def test_bounded_async_results_are_exact(self):
        data = random.Random(17).randbytes(2 * 1024**2)
        with DigestPipeline() as pipeline:
            futures = [pipeline.stream(data + bytes([index])) for index in range(6)]
            expected = [hashlib.sha256(data + bytes([index])).hexdigest() for index in range(6)]
            self.assertEqual([future.result() for future in futures], expected)

    def test_background_hash_failure_is_propagated(self):
        data = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 0x7FFFFFFF) + b"IDAT" + b"x" * 1024**2
        with self.assertRaises(ImageDecodeError):
            with DigestPipeline() as pipeline:
                pipeline.image(data)

    def test_png_digest_is_idat_stream(self):
        data = image_bytes()
        offset = data.index(b"IDAT")
        length = int.from_bytes(data[offset - 4:offset], "big")
        expected = hashlib.sha256(data[offset + 4:offset + 4 + length]).hexdigest()
        self.assertEqual(image_stream_digest(data), expected)

    def test_png_iend_crc_is_checked(self):
        data = bytearray(image_bytes())
        data[-1] ^= 1
        with self.assertRaises(ImageDecodeError):
            inspect_png_chunks(io.BytesIO(data), len(data))

    def test_png_ancillary_metadata_uses_pillow_text_limits(self):
        # A valid zTXt chunk with a small compressed body must not bypass Pillow's
        # decompression protections while pixel decoding is skipped.
        base = image_bytes()
        payload = b"comment\x00\x00" + zlib.compress(b"x" * (1024**2 + 1))
        body = b"zTXt" + payload
        chunk = len(payload).to_bytes(4, "big") + body + zlib.crc32(body).to_bytes(4, "big")
        path = self.archive({"page.png": base[:-12] + chunk + base[-12:]})
        result = convert(path)
        self.assertEqual(result.error_type, "ImageDecodeError")


class PdfResourceTests(ArchiveTestCase):
    def test_dedicated_image_verifier_is_never_skipped(self):
        path = self.archive({"page.jpg": image_bytes("JPEG")})

        def reject_file(image):
            raise SyntaxError("injected dedicated format verification failure")

        with patch.object(JpegImagePlugin.JpegImageFile, "verify", reject_file):
            result = convert(path)
        self.assertFalse(result.ok)
        self.assertIn("dedicated format verification", result.error)
        self.assertTrue(path.exists())
        self.assertFalse(path.with_suffix(".pdf").exists())

    def test_document_image_graph_released_without_garbage_collection(self):
        self.check_released_graph(ConversionConfig(), True)

    def test_document_graph_released_after_failed_write(self):
        self.check_released_graph(ConversionConfig(
            limits=ResourceLimits(max_output_bytes=100)), False)

    def check_released_graph(self, config, success):
        import img2pdf

        build = img2pdf.convert_to_docobject
        references = []

        def capture_graph(*args, **kwargs):
            document = build(*args, **kwargs)
            for obj in document.writer.objects:
                if obj.content.get(b"/Subtype") == b"/Image":
                    references.append(weakref.ref(obj))
            return document

        path = self.archive({"1.jpg": image_bytes("JPEG"), "2.jpg": image_bytes("JPEG")})
        enabled = gc.isenabled()
        gc.disable()
        try:
            with patch("cb2pdf.pdf.img2pdf.convert_to_docobject", side_effect=capture_graph):
                result = convert(path, config=config)
            self.assertEqual(result.ok, success, result.error)
            self.assertTrue(references)
            self.assertTrue(all(reference() is None for reference in references))
            self.assertTrue(path.exists())
            self.assert_clean()
        finally:
            if enabled:
                gc.enable()

    def test_mapping_failure_falls_back_to_independent_file_reads(self):
        path = self.archive()
        with patch("cb2pdf.pdf.mmap.mmap", side_effect=OSError("mapping unavailable")):
            result = convert(path)
        self.assertTrue(result.ok, result.error)

    def test_missing_page_rotation_prevents_commit(self):
        exif = Image.Exif()
        exif[274] = 6
        path = self.archive({"1.jpg": image_bytes("JPEG", exif=exif)})

        def lose_rotation(pages, stream, config):
            # Write a real PDF using an incorrect inspected rotation, then restore
            # the expected record before independent verification.
            original = pages[0].result.rotation_degrees
            pages[0].result.rotation_degrees = 0
            write_pdf(pages, stream, config)
            pages[0].result.rotation_degrees = original

        with patch("cb2pdf.converter.write_pdf", side_effect=lose_rotation):
            result = convert(path)
        self.assertEqual(result.error_type, "PdfVerificationError")
        self.assertFalse(path.with_suffix(".pdf").exists())

    def test_large_reordered_streams_fail_async_verification(self):
        noise = random.Random(43).randbytes(800 * 1000 * 3)
        first = io.BytesIO()
        second = io.BytesIO()
        with Image.frombytes("RGB", (800, 1000), noise) as image:
            image.save(first, "JPEG", quality=95)
            with image.transpose(Image.Transpose.FLIP_LEFT_RIGHT) as reversed_image:
                reversed_image.save(second, "JPEG", quality=95)
        self.assertGreater(len(first.getvalue()), DigestPipeline.minimum_async_bytes)
        path = self.archive({"1.jpg": first.getvalue(), "2.jpg": second.getvalue()})

        def reverse_pages(pages, stream, config):
            write_pdf(list(reversed(pages)), stream, config)

        with patch("cb2pdf.converter.write_pdf", side_effect=reverse_pages):
            result = convert(path)
        self.assertEqual(result.error_type, "PdfVerificationError")
        self.assertTrue(path.exists())
        self.assertFalse(path.with_suffix(".pdf").exists())
        self.assert_clean()
