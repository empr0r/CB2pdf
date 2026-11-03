"""PNG integrity and late metadata inspection without raster decoding.

Pillow's PngImageFile.getexif() loads the raster to find metadata after IDAT.
Use its chunk parser instead: text/ICC protections and chunk CRCs remain active.
Opaque scanlines additionally receive bounded DEFLATE/filter validation without
reconstructing pixels; the full raster is not needed for metadata inspection.
"""

from typing import Any, BinaryIO
from threading import Event
import struct
import zlib

from PIL import ImageFile, PngImagePlugin

from .errors import CancelledError, ImageDecodeError, ResourceLimitError


class ScanlineValidator:
    """Check opaque non-interlaced IDAT without reconstructing a pixel raster.

    Native DEFLATE validates its checksum; scanline extents and filter tags are
    checked in bounded blocks. No RGB array or PNG unfiltering is required.
    """

    _invalid_filter = bytes(5) + b"\x01" * 251

    def __init__(self, header: bytes) -> None:
        width, height = struct.unpack_from(">II", header)
        channels = {0: 1, 2: 3, 3: 1}[header[9]]
        self.stride = (width * channels * header[8] + 7) // 8 + 1
        self.expected_bytes = self.stride * height
        self.decoded_bytes = 0
        self.inflater = zlib.decompressobj()

    def _check_rows(self, data: bytes) -> None:
        if self.decoded_bytes + len(data) > self.expected_bytes:
            raise ResourceLimitError("PNG raster expands beyond its declared dimensions")
        first_filter = (-self.decoded_bytes) % self.stride
        filters = data[first_filter::self.stride]
        if b"\x01" in filters.translate(self._invalid_filter):
            raise ImageDecodeError("invalid PNG scanline filter")
        self.decoded_bytes += len(data)

    def feed(self, data: bytes) -> None:
        view = memoryview(data)
        # Bound unconsumed_tail copies as well as decompressed output blocks.
        for offset in range(0, len(data), 64 * 1024):
            pending: bytes | memoryview = view[offset:offset + 64 * 1024]
            while True:
                maximum = min(1024**2, self.expected_bytes - self.decoded_bytes + 1)
                output = self.inflater.decompress(pending, maximum)
                self._check_rows(output)
                if self.inflater.unused_data:
                    raise ImageDecodeError("unexpected bytes after PNG compressed stream")
                pending = self.inflater.unconsumed_tail
                if not pending and len(output) < maximum:
                    break

    def finish(self) -> None:
        if not self.inflater.eof or self.decoded_bytes != self.expected_bytes:
            raise ImageDecodeError("truncated PNG compressed stream or scanlines")


def inspect_png_chunks(
    stream: BinaryIO, member_bytes: int, cancel: Event | None = None,
) -> dict[str | tuple[int, int], Any]:
    """Return all Pillow metadata, including EXIF/XMP placed after image data."""
    if stream.read(8) != b"\x89PNG\r\n\x1a\n":
        raise ImageDecodeError("invalid PNG signature")
    parser = PngImagePlugin.PngStream(stream)
    consumed = 8
    image_data_seen = False
    header_seen = False
    validator: ScanlineValidator | None = None
    try:
        while True:
            if cancel is not None and cancel.is_set():
                raise CancelledError("conversion cancelled during PNG metadata inspection")
            kind, position, length = parser.read()
            if not header_seen and kind != b"IHDR":
                raise ImageDecodeError("PNG must begin with IHDR")
            if kind in (b"IDAT", b"fdAT"):
                image_data_seen = True
            elif image_data_seen and kind in (
                b"PLTE", b"tRNS", b"iCCP", b"pHYs", b"sRGB", b"gAMA", b"cHRM", b"sBIT", b"bKGD",
            ):
                # Unlike EXIF/text, these color/layout chunks must precede IDAT.
                # Accepting them here while the embedding library reads only the
                # header could silently lose a profile, transparency or native DPI.
                raise ImageDecodeError(f"PNG {kind.decode('ascii')} must precede image data")
            consumed += length + 12
            if consumed > member_bytes:
                raise ImageDecodeError("PNG chunk extends beyond archive member")
            if kind not in (b"IDAT", b"fdAT") and length > 16 * 1024**2:
                raise ResourceLimitError("PNG metadata chunk exceeds 16 MiB")
            # Pillow's frame reader owns APNG sequence/composition validation.
            # Do not overwrite frame-zero metadata with the last frame's controls.
            if kind in (b"IDAT", b"fdAT", b"acTL", b"fcTL", b"IEND"):
                payload = ImageFile._safe_read(stream, length)
            else:
                try:
                    payload = parser.call(kind, position, length)
                except AttributeError:
                    payload = ImageFile._safe_read(stream, length)
            parser.crc(kind, payload)
            if kind == b"IHDR":
                if header_seen:
                    raise ImageDecodeError("duplicate PNG header")
                header_seen = True
                if payload[12] == 0 and payload[9] in (0, 2, 3):
                    validator = ScanlineValidator(payload)
            elif kind == b"acTL":
                # Animated frames use Pillow's composition/decoding path instead.
                validator = None
            elif kind == b"IDAT" and validator is not None:
                validator.feed(payload)
            if kind == b"IEND":
                if length:
                    raise ImageDecodeError("invalid PNG end chunk")
                if validator is not None:
                    validator.finish()
                return dict(parser.im_info)
    except (OSError, SyntaxError, ValueError, struct.error, zlib.error) as exc:
        raise ImageDecodeError(f"invalid PNG chunks: {exc}") from exc
    finally:
        parser.close()
