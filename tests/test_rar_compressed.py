"""Real compressed/solid RAR4 and RAR5 tests using synthetic, redistributable pages."""

import hashlib
import importlib.util
import io
import json
import shutil
import subprocess
from pathlib import Path
from unittest import TestCase, skipUnless
from unittest.mock import patch

from PIL import Image

from cb2pdf.config import ConversionConfig, ResourceLimits
from cb2pdf.converter import convert
from cb2pdf.archives import ArchiveReader
from cb2pdf.rar_backend import parse_sevenzip_decoders, sevenzip_decoders

from .helpers import ArchiveTestCase, page_image

FIXTURES = Path(__file__).parent / "fixtures" / "rar"


@skipUnless(importlib.util.find_spec("rarfile"), "optional rarfile dependency unavailable")
class CompressedRarTests(ArchiveTestCase):
    def _select_backend(self, backend=None):
        import rarfile

        options = {}
        if backend is not None:
            options = {name: name == backend for name in
                       ("unrar", "unar", "bsdtar", "sevenzip", "sevenzip2")}
        try:
            return rarfile.tool_setup(force=True, **options)
        except rarfile.RarCannotExec:
            self.skipTest(f"RAR backend unavailable: {backend or 'any'}")

    def _round_trip(self, backend=None):
        import rarfile

        with patch.object(rarfile, "CURRENT_SETUP", None):
            selected = self._select_backend(backend)
            using_bsdtar = selected.setup["open_cmd"][0] == "BSDTAR_TOOL"
            using_sevenzip = selected.setup["open_cmd"][0] in ("SEVENZIP_TOOL", "SEVENZIP2_TOOL")
            decoders = sevenzip_decoders(selected) if using_sevenzip else frozenset()
            for fixture in sorted(FIXTURES.glob("rar[45]-*.cbr")):
                with self.subTest(backend=backend, fixture=fixture.name):
                    source = self.root / fixture.name
                    shutil.copyfile(fixture, source)
                    original = source.read_bytes()
                    if using_sevenzip:
                        # Independently ask the real decoder to extract this valid
                        # fixture. Missing codecs must produce an actionable app
                        # error; an available decoder still has to preserve pixels.
                        executable = getattr(rarfile, selected.setup["open_cmd"][0])
                        native = subprocess.run(
                            [executable, "e", "-so", "-bb0", "--", str(source.resolve()),
                             "chapter/page1.bmp"], capture_output=True, timeout=30)
                        method = "Rar3" if fixture.name.startswith("rar4") else "Rar5"
                        if method not in decoders:
                            self.assertNotEqual(native.returncode, 0)
                            message = (native.stdout + native.stderr).decode(errors="replace")
                            self.assertIn("unsupportedmethod", "".join(message.lower().split()))
                            result = convert(source)
                            self.assertEqual(result.error_type, "MissingDependencyError")
                            self.assertIn(method, result.error)
                            self.assertFalse(source.with_suffix(".pdf").exists())
                            self.assertEqual(source.read_bytes(), original)
                            self.assert_clean()
                            continue
                        self.assertEqual(native.returncode, 0,
                                         native.stderr.decode(errors="replace"))
                        known = json.loads((FIXTURES / "manifest.json").read_text())
                        self.assertEqual(hashlib.sha256(native.stdout).hexdigest(),
                                         known["members"]["chapter/page1.bmp"])
                    if using_bsdtar and fixture.name == "rar4-solid.cbr":
                        result = convert(source)
                        self.assertEqual(result.error_type, "MissingDependencyError")
                        self.assertIn("solid RAR3/RAR4", result.error)
                        self.assertFalse(source.with_suffix(".pdf").exists())
                        self.assertEqual(source.read_bytes(), original)
                        continue
                    manifest = json.loads((FIXTURES / "manifest.json").read_text())
                    with ArchiveReader(source, ResourceLimits()) as archive:
                        expected = {member.name: archive.read(member) for member in archive.pages()}
                    self.assertEqual(list(expected), [
                        "chapter/page1.bmp", "chapter/page2.bmp", "chapter/page10.png"])
                    for name, raw in expected.items():
                        self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest["members"][name])
                    result = convert(source)
                    self.assertTrue(result.ok, result.error)
                    self.assertEqual([page.member for page in result.pages], list(expected))
                    for index, raw in enumerate(expected.values()):
                        with Image.open(io.BytesIO(raw)) as before:
                            with page_image(source.with_suffix(".pdf"), index) as after:
                                self.assertEqual(before.size, after.size)
                                self.assertEqual(before.convert("RGB").tobytes(),
                                                 after.convert("RGB").tobytes())
                    self.assertEqual(source.read_bytes(), original)
                    self.assert_clean()

    def test_fixture_integrity_and_actual_compression(self):
        import rarfile

        manifest = json.loads((FIXTURES / "manifest.json").read_text())
        self.assertEqual(len(manifest["archives"]), 4)
        for name, digest in manifest["archives"].items():
            with self.subTest(fixture=name):
                path = FIXTURES / name
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
                with rarfile.RarFile(path) as archive:
                    self.assertEqual(archive.is_solid(), "-solid" in name)
                    files = [info for info in archive.infolist() if info.is_file()]
                    self.assertEqual({info.filename for info in files}, set(manifest["members"]))
                    self.assertTrue(any(info.compress_type != rarfile.RAR_M0 for info in files))
                    self.assertLess(sum(info.compress_size for info in files),
                                    sum(info.file_size for info in files))

    def test_default_backend_round_trip(self):
        self._round_trip()

    def test_unrar_round_trip(self):
        self._round_trip("unrar")

    def test_unar_round_trip(self):
        self._round_trip("unar")

    def test_bsdtar_supported_variants_and_solid_rar4_error(self):
        self._round_trip("bsdtar")

    def test_sevenzip_supported_methods_and_missing_codec_errors(self):
        self._round_trip("sevenzip")

    def test_literal_bsdtar_member_selectors(self):
        import rarfile

        manifest = json.loads((FIXTURES / "manifest.json").read_text())["special_names"]
        source = self.root / "special.cbr"
        shutil.copyfile(FIXTURES / "special-names.cbr", source)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), manifest["sha256"])
        with patch.object(rarfile, "CURRENT_SETUP", None):
            self._select_backend("bsdtar")
            with ArchiveReader(source, ResourceLimits()) as archive:
                for member in archive.pages():
                    raw = archive.read(member)
                    self.assertEqual(hashlib.sha256(raw).hexdigest(),
                                     manifest["members"][member.name])
            result = convert(source)
            self.assertTrue(result.ok, result.error)
            self.assertEqual(len(result.pages), 2)

    def test_corrupt_compressed_stream_preserves_source(self):
        import rarfile

        with patch.object(rarfile, "CURRENT_SETUP", None):
            self._select_backend()
            for fixture in sorted(FIXTURES.glob("rar[45]-*.cbr")):
                with self.subTest(fixture=fixture.name):
                    damaged = bytearray(fixture.read_bytes())
                    with rarfile.RarFile(fixture) as archive:
                        member = archive.getinfo("chapter/page1.bmp")
                        offset = member.data_offset + member.compress_size // 2
                    damaged[offset] ^= 0xFF
                    source = self.root / fixture.name
                    source.write_bytes(damaged)
                    result = convert(source)
                    self.assertFalse(result.ok)
                    self.assertFalse(source.with_suffix(".pdf").exists())
                    self.assertEqual(source.read_bytes(), damaged)
                    self.assert_clean()

    def test_compressed_member_limit_preserves_source(self):
        import rarfile

        with patch.object(rarfile, "CURRENT_SETUP", None):
            self._select_backend()
            for fixture in sorted(FIXTURES.glob("rar[45]-*.cbr")):
                with self.subTest(fixture=fixture.name):
                    source = self.root / fixture.name
                    shutil.copyfile(fixture, source)
                    result = convert(source, config=ConversionConfig(
                        limits=ResourceLimits(max_member_bytes=1000)))
                    self.assertEqual(result.error_type, "ResourceLimitError")
                    self.assertTrue(source.exists())
                    self.assertFalse(source.with_suffix(".pdf").exists())
                    self.assert_clean()


class SevenZipMethodTests(TestCase):
    def test_formats_do_not_imply_decoder_availability(self):
        table = "Formats:\n 0 ...F Rar rar r00\nCodecs:\n 0 D 40305 Rar5\n"
        self.assertEqual(parse_sevenzip_decoders(table), frozenset({"Rar5"}))

    def test_all_supported_decoder_methods(self):
        table = "Codecs:\n 0 D 40301 Rar1\n 0 D 40302 Rar2\n 0 D 40303 Rar3\n 0 D 40305 Rar5\n"
        self.assertEqual(parse_sevenzip_decoders(table),
                         frozenset({"Rar1", "Rar2", "Rar3", "Rar5"}))

    def test_encoder_flags_and_other_sections_are_not_decoders(self):
        table = "Codecs:\n 0 E 40303 Rar3\nHashers:\n 0 D 40305 Rar5\n"
        self.assertEqual(parse_sevenzip_decoders(table), frozenset())
