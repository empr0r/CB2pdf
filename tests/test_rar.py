"""Stored RAR3 fixture writer for testing only; all decoding uses rarfile/backends."""

import importlib.util
import struct
import zlib
from unittest import skipUnless
from unittest.mock import patch

from cb2pdf.archives import ArchiveReader
from cb2pdf.config import ResourceLimits
from cb2pdf.converter import convert

from .helpers import ArchiveTestCase, image_bytes


def rar_header(body: bytes) -> bytes:
    return struct.pack("<H", zlib.crc32(body) & 0xFFFF) + body


def stored_rar(entries: dict[str, bytes]) -> bytes:
    data = bytearray(b"Rar!\x1a\x07\x00")
    data.extend(rar_header(struct.pack("<BHH6s", 0x73, 0, 13, b"\0" * 6)))
    for name, content in entries.items():
        encoded = name.encode("ascii")
        body = struct.pack(
            "<BHHIIBIIBBHI", 0x74, 0x8000, 32 + len(encoded),
            len(content), len(content), 3, zlib.crc32(content), 0, 20, 0x30,
            len(encoded), 0o100644,
        ) + encoded
        data.extend(rar_header(body))
        data.extend(content)
    data.extend(rar_header(struct.pack("<BHH", 0x7B, 0, 7)))
    return bytes(data)


@skipUnless(importlib.util.find_spec("rarfile"), "optional rarfile dependency unavailable")
class RarTests(ArchiveTestCase):
    def setUp(self):
        super().setUp()
        import rarfile

        try:
            rarfile.tool_setup()
        except rarfile.RarCannotExec:
            self.skipTest("no compatible external RAR backend")

    def make_rar(self, entries=None):
        path = self.root / "comic.cbr"
        path.write_bytes(stored_rar(
            entries or {"page2.jpg": image_bytes("JPEG"), "page1.png": image_bytes()}))
        return path

    def test_real_stored_rar_conversion(self):
        path = self.make_rar()
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        self.assertEqual([p.member for p in result.pages], ["page1.png", "page2.jpg"])
        self.assertTrue(path.exists())

    def test_rar_byte_limit(self):
        from cb2pdf.errors import ResourceLimitError

        path = self.make_rar()
        with (
            self.assertRaises(ResourceLimitError),
            ArchiveReader(path, ResourceLimits(max_member_bytes=10)),
        ):
            pass

    def test_rar_traversal_refused(self):
        result = convert(self.make_rar({"../page.png": image_bytes()}))
        self.assertEqual(result.error_type, "UnsafeArchiveError")

    def test_missing_rar_backend_actionable(self):
        import rarfile

        with patch("rarfile.tool_setup", side_effect=rarfile.RarCannotExec("missing")):
            result = convert(self.make_rar())
        self.assertEqual(result.error_type, "MissingDependencyError")

    def test_missing_optional_rar_library(self):
        path = self.make_rar()
        with patch.dict("sys.modules", {"rarfile": None}):
            result = convert(path)
        self.assertEqual(result.error_type, "MissingDependencyError")
