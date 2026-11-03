import io
import zipfile

from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject, ByteStringObject, DecodedStreamObject, DictionaryObject,
    EncodedStreamObject, NameObject, NumberObject,
)

from benchmarks.real_world import digest, repack_pdf

from .helpers import ArchiveTestCase


class RealFixtureTests(ArchiveTestCase):
    def test_indexed_asciihex_palette_survives_fixture_export(self):
        source = self.root / "source.pdf"
        writer = PdfWriter()
        page = writer.add_blank_page(3, 2)
        image = EncodedStreamObject()
        image._data = b"000100010001>"
        image.update({
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(3),
            NameObject("/Height"): NumberObject(2),
            NameObject("/BitsPerComponent"): NumberObject(8),
            NameObject("/Filter"): NameObject("/ASCIIHexDecode"),
            NameObject("/ColorSpace"): ArrayObject([
                NameObject("/Indexed"), NameObject("/DeviceRGB"), NumberObject(1),
                ByteStringObject(b"\xff\xff\xff\x00\x00\x00"),
            ]),
        })
        page[NameObject("/Resources")] = DictionaryObject({
            NameObject("/XObject"): DictionaryObject({
                NameObject("/Im0"): writer._add_object(image),
            }),
        })
        contents = DecodedStreamObject()
        contents.set_data(b"q 3 0 0 2 0 0 cm /Im0 Do Q")
        page[NameObject("/Contents")] = writer._add_object(contents)
        writer.write(source)
        writer.close()
        before = digest(source)
        destination = self.root / "fixture.cbz"
        result = repack_pdf(source, destination)
        self.assertEqual(result["pages"], 1)
        self.assertEqual(digest(source), before)
        with zipfile.ZipFile(destination) as archive:
            with Image.open(io.BytesIO(archive.read("page00001.png"))) as actual:
                rgb = actual.convert("RGB")
                self.assertEqual(rgb.getpixel((0, 0)), (255, 255, 255))
                self.assertEqual(rgb.getpixel((1, 0)), (0, 0, 0))
