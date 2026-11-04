import stat
import struct
import warnings
import zipfile
from dataclasses import replace

from cb2pdf.archives import ArchiveReader, detect_format, is_image_member, validate_member_name
from cb2pdf.config import ResourceLimits
from cb2pdf.converter import convert
from cb2pdf.errors import ResourceLimitError, UnsafeArchiveError
from cb2pdf.ordering import natural_key

from .helpers import ArchiveTestCase, image_bytes


class ArchiveTests(ArchiveTestCase):
    def test_signatures_override_extensions(self):
        path = self.archive(name="misnamed.cbr")
        self.assertEqual(detect_format(path), "zip")
        self.assertTrue(convert(path).ok)

    def test_arbitrary_input_rejected(self):
        path = self.root / "bad.cbz"
        path.write_bytes(b"ordinary text")
        result = convert(path)
        self.assertEqual(result.error_type, "ArchiveFormatError")
        self.assertTrue(path.exists())

    def test_empty_archive_fails(self):
        path = self.root / "empty.cbz"
        with zipfile.ZipFile(path, "w"):
            pass
        self.assertFalse(convert(path).ok)
        self.assertFalse(path.with_suffix(".pdf").exists())

    def test_nested_unicode_and_metadata(self):
        path = self.archive({
            "章/page10.PNG": image_bytes(), "章/page2.png": image_bytes(),
            "__MACOSX/._page1.png": b"ignored", ".hidden/a.png": b"ignored",
            "ComicInfo.xml": b"ignored", "a.gif.txt": b"ignored",
        })
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        self.assertEqual([p.member for p in result.pages], ["章/page2.png", "章/page10.PNG"])

    def test_path_traversal_and_absolute_paths(self):
        for name in (
            "../page.jpg", "/page.jpg", "C:\\page.jpg", "a\\..\\page.jpg",
            "a:stream.png", "a/./1.png",
        ):
            with self.subTest(name=name), self.assertRaises(UnsafeArchiveError):
                validate_member_name(name)

    def test_unsafe_nonimage_members_also_rejected(self):
        path = self.archive({"1.png": image_bytes(), "../../bad.txt": b"no"})
        self.assertEqual(convert(path).error_type, "UnsafeArchiveError")

    def test_nul_in_original_zip_name_rejected(self):
        path = self.archive({"1.pngx": image_bytes()})
        path.write_bytes(path.read_bytes().replace(b"1.pngx", b"1.png\0"))
        self.assertEqual(convert(path).error_type, "UnsafeArchiveError")

    def test_symlink_rejected(self):
        path = self.root / "links.cbz"
        with zipfile.ZipFile(path, "w") as archive:
            info = zipfile.ZipInfo("link.png")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "target")
        self.assertEqual(convert(path).error_type, "UnsafeArchiveError")

    def test_duplicate_names_rejected(self):
        path = self.archive()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with zipfile.ZipFile(path, "a") as archive:
                archive.writestr("1.png", image_bytes())
        self.assertEqual(convert(path).error_type, "UnsafeArchiveError")

    def test_unicode_normalization_duplicate_rejected(self):
        path = self.archive({"é.png": image_bytes(), "e\u0301.png": image_bytes()})
        self.assertEqual(convert(path).error_type, "UnsafeArchiveError")

    def test_case_ambiguity_reported(self):
        path = self.archive({"A.png": image_bytes(), "a.png": image_bytes()})
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        self.assertEqual(len(result.warnings), 1)

    def test_member_count_preflight(self):
        path = self.archive({"1.png": image_bytes(), "2.png": image_bytes()})
        with (
            self.assertRaises(ResourceLimitError),
            ArchiveReader(path, ResourceLimits(max_members=1)),
        ):
            pass

    def test_declared_byte_and_ratio_limits(self):
        path = self.archive({"1.png": image_bytes(), "padding.txt": b"0" *
                            10_000}, compression=zipfile.ZIP_DEFLATED)
        for limits in (
            ResourceLimits(max_member_bytes=100), ResourceLimits(max_total_bytes=100),
            ResourceLimits(max_compression_ratio=2),
        ):
            with self.subTest(limits=limits), self.assertRaises(ResourceLimitError):
                with ArchiveReader(path, limits):
                    pass

    def test_zip_crc_failure_preserves_original(self):
        path = self.archive({"1.jpg": image_bytes("JPEG")})
        data = bytearray(path.read_bytes())
        name_len, extra_len = struct.unpack_from("<HH", data, 26)
        offset = 30 + name_len + extra_len
        data[offset + 40] ^= 1
        path.write_bytes(data)
        result = convert(path)
        self.assertFalse(result.ok)
        self.assertTrue(path.exists())
        self.assertFalse(path.with_suffix(".pdf").exists())
        self.assert_clean()

    def test_zip_comment_and_backslash_paths(self):
        path = self.archive({"chapter\\page1.jpg": image_bytes("JPEG")})
        with zipfile.ZipFile(path, "a") as archive:
            archive.comment = b"ordinary ZIP comment"
        self.assertTrue(convert(path).ok)

    def test_truncated_zip(self):
        path = self.archive()
        path.write_bytes(path.read_bytes()[:-30])
        self.assertEqual(convert(path).error_type, "ArchiveCorruptionError")

    def test_image_suffix_filter(self):
        for name in ("foo.TIF", "x/y.webp", "x\\y.GIF"):
            self.assertTrue(is_image_member(name))
        for name in ("notjpg", "1.png.exe", "._1.png", "__MACOSX/1.png"):
            self.assertFalse(is_image_member(name))

    def test_actual_member_size_is_checked(self):
        path = self.archive()
        with ArchiveReader(path, ResourceLimits()) as archive:
            member = archive.pages()[0]
            with self.assertRaises(ResourceLimitError):
                archive.read(replace(member, size=member.size - 1))


class OrderingTests(ArchiveTestCase):
    def test_numeric_directory_and_leading_zeros(self):
        names = ["Chapter 2/page1.png", "Chapter 01/page10.png",
                 "Chapter 01/page02.png", "Chapter 01/page2.png", "Chapter 01/page1.png"]
        self.assertEqual(sorted(names, key=natural_key), [
                         names[4], names[3], names[2], names[1], names[0]])

    def test_order_independent_of_enumeration(self):
        names = ["Page1.png", "page1.png", "page10.png", "page2.png", "é/1.png"]
        self.assertEqual(sorted(names, key=natural_key), sorted(reversed(names), key=natural_key))
