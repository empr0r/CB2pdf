"""Image inspection and lazy, one-page-at-a-time normalization."""

import io
from concurrent.futures import Future
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

from .archives import ArchiveReader, check_cancelled
from .config import ConversionConfig, Quality
from .digests import DigestPipeline, image_stream_digest
from .errors import ImageDecodeError, ResourceLimitError
from .models import ArchiveMember, ImageMetadata, PageResult
from .png import inspect_png_chunks

SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "GIF", "TIFF"}


def _metadata(image: Image.Image, frames: int, config: ConversionConfig) -> ImageMetadata:
    if image.width * image.height > config.limits.max_pixels:
        raise ResourceLimitError(
            f"image {image.width}x{image.height} exceeds {config.limits.max_pixels} pixels"
        )
    if image.format == "PNG":
        # Complete chunk metadata was collected without reconstructing pixels. Bypass
        # PngImageFile.getexif(), whose implementation forces raster decoding.
        exif = Image.Image.getexif(image)
    else:
        exif = image.getexif()
    orientation = int(exif.get(274, 1))
    if orientation not in range(1, 9):
        raise ImageDecodeError(
            f"invalid EXIF orientation {orientation}; repair the source metadata")
    if image.mode in ("F", "I") and image.format != "PNG":
        raise ImageDecodeError(
            "floating-point and 32-bit integer samples cannot be preserved in PDF")
    return ImageMetadata(
        image.format or "", image.mode, image.width, image.height, frames, orientation,
        "A" in image.getbands() or "transparency" in image.info,
        bool(image.info.get("icc_profile")),
        bool(getattr(image, "is_animated", False)
             or getattr(image, "custom_mimetype", None) == "image/apng"),
    )


def inspect_member(
    archive: ArchiveReader, member: ArchiveMember, config: ConversionConfig
) -> list[ImageMetadata]:
    """Inspect every frame; retain Pillow's decompression bomb protections.

    Default JPEG inspection checks headers rather than decoding all pixels. Use
    decode_verify to additionally test pixel decoding before embedding.
    """
    try:
        with archive.open(member) as stream, Image.open(stream) as image:
            if image.format not in SUPPORTED_FORMATS:
                raise ImageDecodeError(f"unsupported image content: {image.format}")
            if image.width * image.height > config.limits.max_pixels:
                raise ResourceLimitError("image exceeds configured pixel limit")
            png = image.format == "PNG"
            base_verifier = type(image).verify is Image.Image.verify
            if png:
                with archive.open(member) as chunks:
                    image.info.update(inspect_png_chunks(chunks, member.size, archive.cancel))
            _metadata(image, 1, config)
            frames = getattr(image, "n_frames", 1)
            if frames > config.limits.max_pages:
                raise ResourceLimitError(f"too many image frames in {member.name!r}")
            if frames > 1 and config.frames == "reject":
                raise ImageDecodeError(f"{member.name!r} has {frames} frames; --frames reject")
            metadata = []
            for frame in range(frames):
                check_cancelled(archive.cancel)
                image.seek(frame)
                metadata.append(_metadata(image, frames, config))
                if config.decode_verify:
                    image.load()
            if not png and base_verifier:
                # The base verifier is a placeholder, not a fresh-file parser.
                # Keep the call without reopening/re-reading the same headers.
                image.verify()
            # Dedicated plugin verifiers can depend on fresh seek/decode state;
            # preserve their separate read, while PNG checks use our chunk path.
        if not png and not base_verifier:
            with archive.open(member) as stream, Image.open(stream) as image:
                image.verify()
        return metadata
    except (ResourceLimitError, ImageDecodeError):
        raise
    except (
        UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError,
    ) as exc:
        raise ImageDecodeError(f"invalid image {member.name!r}: {exc}") from exc


@dataclass
class InputBudget:
    limit: int
    used: int = 0

    def consume(self, size: int) -> None:
        self.used += size
        if self.used > self.limit:
            raise ResourceLimitError("encoded PDF image inputs exceed configured document budget")


class ImageInput:
    """A lazy img2pdf read() source, retaining no compressed or decoded image data."""

    def __init__(
        self,
        archive: ArchiveReader,
        member: ArchiveMember,
        metadata: ImageMetadata,
        frame: int,
        config: ConversionConfig,
        budget: InputBudget,
        staged: Path | None = None,
    ) -> None:
        self.archive = archive
        self.member = member
        self.metadata = metadata
        self.frame = frame
        self.config = config
        self.budget = budget
        self.staged = staged
        width, height = metadata.width, metadata.height
        if metadata.orientation in (5, 6, 7, 8):
            width, height = height, width
        self.result = PageResult(member.name, frame + 1, width, height)
        self.result.rotation_degrees = {3: 180, 6: 90, 8: 270}.get(metadata.orientation, 0)
        self.digest_pipeline: DigestPipeline | None = None
        self._digest_future: Future[str] | None = None

    def read(self) -> bytes:
        check_cancelled(self.archive.cancel)
        raw = self.staged.read_bytes() if self.staged else self.archive.read(self.member)
        try:
            data = self._prepare(raw)
        except (ResourceLimitError, ImageDecodeError):
            raise
        except (
            OSError, ValueError, SyntaxError, Image.DecompressionBombError, ImageCms.PyCMSError,
        ) as exc:
            raise ImageDecodeError(f"normalizing {self.member.name!r}: {exc}") from exc
        # Non-direct encodings can expand dramatically inside img2pdf. Charge a
        # conservative sample-size bound, including an alpha plane, before handing
        # these images to the library. The graph's budget cannot be bypassed by a
        # tiny WebP/GIF or by palette/transparency expansion.
        direct = data.startswith(b"\xff\xd8")
        if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) > 28:
            direct = data[28] == 0 and data[25] in (0, 2, 3) and not self.metadata.has_alpha
        accounted = len(data)
        if not direct:
            accounted = max(accounted, self.result.width * self.result.height * 8)
        self.budget.consume(accounted)
        if direct:
            if self.digest_pipeline is not None:
                self._digest_future = self.digest_pipeline.image(data)
            else:
                self.result.direct_stream_sha256 = image_stream_digest(data)
        self.result.encoded_bytes = len(data)
        return data

    def finish_digest(self) -> None:
        """Transfer a completed digest into the serializable page result."""
        if self._digest_future is not None:
            self.result.direct_stream_sha256 = self._digest_future.result()
            self._digest_future = None

    def _prepare(self, raw: bytes) -> bytes:
        metadata, config = self.metadata, self.config
        maximum = config.effective_max_size
        resize = maximum is not None and (
            self.result.width > maximum[0]
            or self.result.height > maximum[1]
            or config.upscale
        )
        lossy = config.quality is not Quality.LOSSLESS and (
            not metadata.has_alpha or config.flatten_alpha
        )
        normalize = (
            metadata.frames > 1
            or metadata.is_animated
            or metadata.orientation in (2, 4, 5, 7)
            or (config.page_size is not None and metadata.orientation != 1)
            or resize
            or lossy
            or (metadata.has_alpha and config.flatten_alpha)
        )
        if not normalize:
            if metadata.format not in ("JPEG", "PNG"):
                self.result.transformations.append(f"lossless PDF encoding from {metadata.format}")
            return raw
        with Image.open(io.BytesIO(raw)) as original:
            original.seek(self.frame)
            with ImageOps.exif_transpose(original) as image:
                self.result.rotation_degrees = 0
                transformations = self.result.transformations
                if metadata.frames > 1:
                    transformations.append(f"expanded frame {self.frame + 1}/{metadata.frames}")
                if metadata.orientation != 1:
                    transformations.append("applied EXIF orientation to pixels")
                if resize and maximum is not None:
                    if image.mode == "P":
                        converted = image.convert("RGBA" if metadata.has_alpha else "RGB")
                        image.close()
                        image = converted
                    ratio = min(maximum[0] / image.width, maximum[1] / image.height)
                    if not config.upscale:
                        ratio = min(1.0, ratio)
                    size = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
                    if size[0] * size[1] > config.limits.max_pixels:
                        raise ResourceLimitError("requested resize exceeds pixel limit")
                    if size != image.size:
                        resized = image.resize(size, Image.Resampling.LANCZOS)
                        image.close()
                        image = resized
                        transformations.append(f"resized to {size[0]}x{size[1]}")
                icc = image.info.get("icc_profile")
                if metadata.has_alpha and config.flatten_alpha:
                    with image.convert("RGBA") as rgba:
                        background = Image.new("RGBA", image.size, (*config.background, 255))
                        background.alpha_composite(rgba)
                        flattened = background.convert("RGB")
                        background.close()
                    image.close()
                    image = flattened
                    transformations.append(f"flattened alpha on RGB {config.background}")
                if lossy and image.mode not in ("RGB", "L"):
                    if image.mode == "CMYK" and icc:
                        managed = ImageCms.profileToProfile(
                            image, ImageCms.ImageCmsProfile(io.BytesIO(icc)),
                            ImageCms.createProfile("sRGB"), outputMode="RGB",
                        )
                        if managed is None:
                            raise ImageDecodeError("ICC color conversion returned no image")
                        converted = managed
                        icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
                        transformations.append("color-managed CMYK to sRGB")
                    else:
                        converted = image.convert("RGB")
                    image.close()
                    image = converted
                try:
                    buffer = io.BytesIO()
                    save_options = {}
                    if icc:
                        save_options["icc_profile"] = icc
                    native_dpi = original.info.get("dpi")
                    if native_dpi is not None:
                        save_options["dpi"] = native_dpi
                    if lossy:
                        image.save(
                            buffer, format="JPEG", quality=config.effective_jpeg_quality,
                            subsampling=0, **save_options,
                        )
                        transformations.append(
                            f"lossy JPEG quality {config.effective_jpeg_quality}")
                    elif image.mode == "CMYK":
                        image.save(buffer, format="TIFF",
                                   compression="tiff_deflate", **save_options)
                    else:
                        image.save(buffer, format="PNG", **save_options)
                        transformations.append("lossless PNG normalization")
                    self.result.width, self.result.height = image.size
                    return buffer.getvalue()
                finally:
                    image.close()


def prepare_pages(
    archive: ArchiveReader, config: ConversionConfig, workspace: Path
) -> list[ImageInput]:
    pages: list[ImageInput] = []
    budget = InputBudget(config.limits.max_pdf_input_bytes)
    declared_page_bytes = 0
    for member in archive.pages(config.ordering):
        check_cancelled(archive.cancel)
        metadata = inspect_member(archive, member, config)
        if len(pages) + len(metadata) > config.limits.max_pages:
            raise ResourceLimitError("document page count exceeds configured limit")
        declared_page_bytes += member.size
        if declared_page_bytes > config.limits.max_pdf_input_bytes:
            raise ResourceLimitError("selected image data exceeds PDF input budget")
        staged = None
        if len(metadata) > 1 and not config.dry_run:
            # Repeatedly seeking compressed archive streams is especially costly for
            # animated formats. Stage only these members, under application-owned names.
            staged = workspace / f"multiframe-{member.index}.image"
            staged.write_bytes(archive.read(member))
        for frame, info in enumerate(metadata):
            pages.append(ImageInput(archive, member, info, frame, config, budget, staged))
    if not pages:
        raise ImageDecodeError("archive contains no supported visible image members")
    return pages
