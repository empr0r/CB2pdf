import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader


def image_bytes(
    format: str = "PNG", size: tuple[int, int] = (64, 96), mode: str = "RGB",
    color: object = (30, 80, 150), **options: object,
) -> bytes:
    buffer = io.BytesIO()
    with Image.new(mode, size, color) as image:
        image.save(buffer, format=format, **options)
    return buffer.getvalue()


def page_image(path: Path, page: int = 0) -> Image.Image:
    with path.open("rb") as stream:
        return PdfReader(stream).pages[page].images[0].image.copy()


class ArchiveTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)

    def archive(
        self, entries: dict[str, bytes] | None = None, name: str = "comic.cbz", **options: object,
    ) -> Path:
        path = self.root / name
        with zipfile.ZipFile(path, "w", **options) as archive:
            for filename, data in (entries or {"1.png": image_bytes()}).items():
                archive.writestr(filename, data)
        return path

    def assert_clean(self) -> None:
        self.assertEqual(list(self.root.rglob("*.cb2pdf-part")), [])
