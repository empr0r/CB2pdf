"""Established image embedding and independent PDF completeness verification."""

from pathlib import Path
import hashlib
from typing import BinaryIO

import img2pdf
from pypdf import PdfReader
from pypdf.generic import DictionaryObject, StreamObject

from .config import ConversionConfig
from .errors import ConversionError, PdfGenerationError, PdfVerificationError, ResourceLimitError
from .images import ImageInput
from .models import VerificationResult


class LimitedOutput:
    """Enforce an output size ceiling while img2pdf serializes to an owned stream."""

    def __init__(self, stream: BinaryIO, limit: int) -> None:
        self.stream = stream
        self.limit = limit
        self.written = 0

    def write(self, data: bytes) -> int:
        if self.written + len(data) > self.limit:
            raise ResourceLimitError("PDF exceeds configured output byte limit")
        count = self.stream.write(data)
        self.written += count
        return count


def write_pdf(pages: list[ImageInput], stream: BinaryIO, config: ConversionConfig) -> None:
    """Write without building a second complete PDF byte string.

    img2pdf's internal engine still retains compressed image streams in its object
    graph. InputBudget bounds their aggregate input size; this is not constant memory.
    """
    layout = img2pdf.default_layout_fun
    if config.page_size is not None:
        layout = img2pdf.get_layout_fun(config.page_size)
    if config.dpi is not None:
        base_layout = layout

        def layout(width: int, height: int, native_dpi: tuple[float, float]) -> tuple:
            return base_layout(width, height, (config.dpi, config.dpi))

    try:
        img2pdf.convert(
            pages,
            outputstream=LimitedOutput(stream, config.limits.max_output_bytes),
            engine=img2pdf.Engine.internal,
            layout_fun=layout,
            title=config.title,
            author=config.author,
            subject=config.subject,
            keywords=list(config.keywords) or None,
            creator="CB2pdf",
            nodate=True,
            first_frame_only=False,
            rotation=img2pdf.Rotation.auto,
        )
    except ConversionError:
        raise
    except Exception as exc:
        raise PdfGenerationError(f"PDF image embedding failed: {exc}") from exc


def verify_pdf(path: Path, pages: list[ImageInput]) -> VerificationResult:
    """Parse finalized output strictly, validate pages, content and image resources.

    This is structural verification, not a raster rendering of every page. Integration
    tests additionally compare extracted pixels and original compressed JPEG streams.
    """
    reader = None
    try:
        size = path.stat().st_size
        with path.open("rb") as stream:
            if stream.read(5) != b"%PDF-":
                raise PdfVerificationError("missing PDF signature")
            stream.seek(max(0, size - 64))
            if not stream.read().rstrip().endswith(b"%%EOF"):
                raise PdfVerificationError("PDF was not finalized")
            stream.seek(0)
            reader = PdfReader(stream, strict=True)
            if reader.is_encrypted:
                raise PdfVerificationError("unexpected encrypted PDF")
            if len(reader.pages) != len(pages):
                raise PdfVerificationError(
                    f"expected {len(pages)} pages, found {len(reader.pages)}"
                )
            for index, (page, expected) in enumerate(zip(reader.pages, pages, strict=True)):
                if page.mediabox.width <= 0 or page.mediabox.height <= 0:
                    raise PdfVerificationError(f"invalid dimensions on page {index + 1}")
                contents = page.get_contents()
                if contents is None or not contents.get_data():
                    raise PdfVerificationError(f"empty content on page {index + 1}")
                resources = page["/Resources"].get_object()
                if not isinstance(resources, DictionaryObject):
                    raise PdfVerificationError(f"invalid resources on page {index + 1}")
                objects = resources["/XObject"].get_object()
                if not isinstance(objects, DictionaryObject):
                    raise PdfVerificationError(f"invalid image resources on page {index + 1}")
                images = [obj.get_object() for obj in objects.values()]
                if (
                    len(images) != 1 or not isinstance(images[0], DictionaryObject)
                    or images[0].get("/Subtype") != "/Image"
                ):
                    raise PdfVerificationError(f"missing page image on page {index + 1}")
                image = images[0]
                if not isinstance(image, DictionaryObject):
                    raise PdfVerificationError(f"invalid image dictionary on page {index + 1}")
                width, height = image["/Width"], image["/Height"]
                if not isinstance(width, int) or not isinstance(height, int):
                    raise PdfVerificationError(f"non-integer image dimensions on page {index + 1}")
                actual = (int(width), int(height))
                wanted = (expected.result.width, expected.result.height)
                if actual != wanted:
                    if expected.metadata.orientation not in (5, 6, 7, 8) or actual != wanted[::-1]:
                        raise PdfVerificationError(f"wrong image dimensions on page {index + 1}")
                if image.get("/Length", 1) <= 0:
                    raise PdfVerificationError(f"empty image on page {index + 1}")
                digest = expected.result.direct_stream_sha256
                if digest is not None:
                    if not isinstance(image, StreamObject):
                        raise PdfVerificationError(f"missing image stream on page {index + 1}")
                    if hashlib.sha256(image._data).hexdigest() != digest:
                        raise PdfVerificationError(
                            f"image stream or page order mismatch on page {index + 1}"
                        )
        return VerificationResult(len(pages), len(pages), size)
    except PdfVerificationError:
        raise
    except Exception as exc:
        raise PdfVerificationError(f"cannot read generated PDF: {exc}") from exc
    finally:
        if reader is not None:
            reader.close()
