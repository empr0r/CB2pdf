import io
import shutil
import subprocess
from unittest import skipUnless

from PIL import Image, ImageChops, ImageOps
from pypdf import PdfReader

from cb2pdf.config import ConversionConfig, Quality, ResourceLimits
from cb2pdf.converter import convert

from .helpers import ArchiveTestCase, image_bytes, page_image


class ImagePdfTests(ArchiveTestCase):
    def test_jpeg_compressed_stream_exact(self):
        data = image_bytes("JPEG")
        path = self.archive({"1.jpg": data})
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        page = PdfReader(path.with_suffix(".pdf")).pages[0]
        obj = next(iter(page["/Resources"]["/XObject"].values())).get_object()
        self.assertEqual(obj._data, data)
        self.assertEqual(result.normalized_pages, 0)

    def test_lossless_pixels_and_order(self):
        entries = {f"page{n}.png": image_bytes(color=(n * 20, 50, 150)) for n in [10, 2, 1]}
        path = self.archive(entries)
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        for index, n in enumerate([1, 2, 10]):
            with Image.open(io.BytesIO(entries[f"page{n}.png"])) as source:
                self.assertIsNone(ImageChops.difference(
                    source, page_image(path.with_suffix(".pdf"), index)).getbbox())

    def test_all_target_formats(self):
        formats = {"1.jpg": "JPEG", "2.png": "PNG", "3.webp": "WEBP",
                   "4.bmp": "BMP", "5.gif": "GIF", "6.tif": "TIFF"}
        path = self.archive({name: image_bytes(format) for name, format in formats.items()})
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        self.assertEqual(len(PdfReader(path.with_suffix(".pdf")).pages), 6)

    def test_alpha_preserved(self):
        path = self.archive({"1.png": image_bytes(mode="RGBA", color=(20, 60, 100, 90))})
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        page = PdfReader(path.with_suffix(".pdf")).pages[0]
        obj = next(iter(page["/Resources"]["/XObject"].values())).get_object()
        self.assertIn("/SMask", obj)
        self.assertEqual(page_image(path.with_suffix(".pdf")).convert(
            "RGBA").getpixel((0, 0)), (20, 60, 100, 90))

    def test_background_flattening_explicit(self):
        path = self.archive({"1.png": image_bytes(mode="RGBA", color=(200, 0, 0, 0))})
        result = convert(path, config=ConversionConfig(flatten_alpha=True, background=(10, 20, 30)))
        self.assertTrue(result.ok, result.error)
        self.assertEqual(page_image(path.with_suffix(".pdf")).convert(
            "RGB").getpixel((0, 0)), (10, 20, 30))
        self.assertTrue(any("flattened" in t for t in result.pages[0].transformations))

    def test_animated_gif_and_multipage_tiff_expand(self):
        for format in ("GIF", "TIFF", "WEBP"):
            with self.subTest(format=format):
                buffer = io.BytesIO()
                images = [Image.new("RGB", (50, 60), c) for c in ("red", "blue")]
                images[0].save(buffer, format, save_all=True,
                               append_images=images[1:], duration=100)
                for image in images:
                    image.close()
                path = self.archive({f"1.{format.lower()}": buffer.getvalue()},
                                    name=f"{format}.cbz")
                result = convert(path)
                self.assertTrue(result.ok, result.error)
                self.assertEqual(len(result.pages), 2)
                first = page_image(path.with_suffix(".pdf"), 0).convert("RGB").getpixel((0, 0))
                second = page_image(path.with_suffix(".pdf"), 1).convert("RGB").getpixel((0, 0))
                self.assertGreater(first[0], 240)
                self.assertGreater(second[2], 240)

    def test_frame_rejection_is_explicit(self):
        buffer = io.BytesIO()
        with (
            Image.new("RGB", (10, 10), "red") as first,
            Image.new("RGB", (10, 10), "blue") as second,
        ):
            first.save(buffer, "TIFF", save_all=True, append_images=[second])
        path = self.archive({"1.tiff": buffer.getvalue()})
        result = convert(path, config=ConversionConfig(frames="reject"))
        self.assertEqual(result.error_type, "ImageDecodeError")

    def test_every_exif_orientation(self):
        with Image.new("RGB", (20, 40), "red") as image:
            for y in range(20, 40):
                for x in range(20):
                    image.putpixel((x, y), (0, 0, 255))
            for orientation in range(1, 9):
                with self.subTest(orientation=orientation):
                    exif = Image.Exif()
                    exif[274] = orientation
                    buffer = io.BytesIO()
                    image.save(buffer, "PNG", exif=exif)
                    path = self.archive({"1.png": buffer.getvalue()},
                                        name=f"orientation{orientation}.cbz")
                    result = convert(path)
                    self.assertTrue(result.ok, result.error)
                    page = PdfReader(path.with_suffix(".pdf")).pages[0]
                    ratio = float(page.mediabox.width / page.mediabox.height)
                    if int(page.get("/Rotate", 0)) % 180:
                        ratio = 1 / ratio
                    self.assertAlmostEqual(ratio, 2.0 if orientation >= 5 else 0.5, places=4)
                    if orientation in (2, 4, 5, 7):
                        with Image.open(io.BytesIO(buffer.getvalue())) as source:
                            expected = ImageOps.exif_transpose(source)
                            actual = page_image(path.with_suffix(".pdf"))
                            self.assertIsNone(ImageChops.difference(expected, actual).getbbox())

    def test_resize_optional_no_upscale(self):
        path = self.archive()
        result = convert(path, config=ConversionConfig(max_size=(32, 32)))
        self.assertTrue(result.ok, result.error)
        self.assertEqual((result.pages[0].width, result.pages[0].height), (21, 32))
        result = convert(path, config=ConversionConfig(max_size=(1000, 1000), overwrite=True))
        self.assertTrue(result.ok, result.error)
        self.assertEqual((result.pages[0].width, result.pages[0].height), (64, 96))

    def test_default_preserves_large_dimensions(self):
        path = self.archive({"1.jpg": image_bytes("JPEG", size=(2600, 100))})
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.pages[0].width, 2600)
        self.assertEqual(result.normalized_pages, 0)

    def test_quality_profiles_report_loss(self):
        for quality in (Quality.BALANCED, Quality.SMALL):
            path = self.archive(name=f"{quality.value}.cbz")
            result = convert(path, config=ConversionConfig(quality=quality))
            self.assertTrue(result.ok, result.error)
            self.assertTrue(any("lossy JPEG" in t for t in result.pages[0].transformations))

    def test_cmyk_and_grayscale(self):
        path = self.archive({
            "1.jpg": image_bytes("JPEG", mode="CMYK", color=(10, 20, 30, 40)),
            "2.png": image_bytes(mode="L", color=40),
        })
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        obj = next(iter(PdfReader(path.with_suffix(".pdf")
                                  ).pages[0]["/Resources"]["/XObject"].values())).get_object()
        self.assertEqual(obj["/ColorSpace"], "/DeviceCMYK")

    def test_page_layout_dpi_and_metadata(self):
        path = self.archive()
        config = ConversionConfig(page_size=(612, 792), dpi=300, title="Comic",
                                  author="A", subject="S", keywords=("one", "two"))
        result = convert(path, config=config)
        self.assertTrue(result.ok, result.error)
        pdf = PdfReader(path.with_suffix(".pdf"))
        self.assertEqual(tuple(pdf.pages[0].mediabox), (0, 0, 612, 792))
        self.assertEqual(pdf.metadata.title, "Comic")

    def test_dpi_changes_page_dimensions(self):
        path = self.archive()
        result = convert(path, config=ConversionConfig(dpi=72))
        self.assertTrue(result.ok, result.error)
        self.assertEqual(tuple(PdfReader(path.with_suffix(
            ".pdf")).pages[0].mediabox), (0, 0, 64, 96))

    def test_limits_on_pixels_pages_output_and_pdf_inputs(self):
        path = self.archive({"1.png": image_bytes(), "2.png": image_bytes()})
        for limit in (
            ResourceLimits(max_pixels=100), ResourceLimits(max_pages=1),
            ResourceLimits(max_output_bytes=100), ResourceLimits(max_pdf_input_bytes=100),
        ):
            result = convert(path, config=ConversionConfig(limits=limit))
            self.assertEqual(result.error_type, "ResourceLimitError", result.error)
            self.assertFalse(path.with_suffix(".pdf").exists())
            self.assert_clean()

    def test_invalid_page_prevents_partial_pdf(self):
        path = self.archive({"1.png": image_bytes(), "2.png": b"invalid"})
        result = convert(path)
        self.assertFalse(result.ok)
        self.assertTrue(path.exists())
        self.assertFalse(path.with_suffix(".pdf").exists())

    def test_small_compressed_images_cannot_bypass_memory_budget(self):
        path = self.archive({"1.webp": image_bytes("WEBP")})
        result = convert(path, config=ConversionConfig(
            limits=ResourceLimits(max_pdf_input_bytes=2000)))
        self.assertEqual(result.error_type, "ResourceLimitError")
        self.assertFalse(path.with_suffix(".pdf").exists())

    def test_high_bit_depth_png(self):
        buffer = io.BytesIO()
        with Image.new("I;16", (20, 30), 32000) as image:
            image.save(buffer, "PNG")
        path = self.archive({"1.png": buffer.getvalue()})
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        page = PdfReader(path.with_suffix(".pdf")).pages[0]
        obj = next(iter(page["/Resources"]["/XObject"].values())).get_object()
        self.assertEqual(obj["/BitsPerComponent"], 16)

    def test_icc_profile_preserved(self):
        from PIL import ImageCms

        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        path = self.archive({"1.jpg": image_bytes("JPEG", icc_profile=profile)})
        result = convert(path)
        self.assertTrue(result.ok, result.error)
        page = PdfReader(path.with_suffix(".pdf")).pages[0]
        obj = next(iter(page["/Resources"]["/XObject"].values())).get_object()
        self.assertEqual(obj["/ColorSpace"][0], "/ICCBased")
        self.assertEqual(obj["/ColorSpace"][1].get_object().get_data(), profile)

    @skipUnless(shutil.which("pdftoppm"), "optional Poppler renderer unavailable")
    def test_rendered_orientation_all_eight_modes(self):
        for orientation in range(1, 9):
            with self.subTest(orientation=orientation):
                with Image.new("RGB", (20, 40), "red") as image:
                    image.paste("blue", (0, 20, 20, 40))
                    exif = Image.Exif()
                    exif[274] = orientation
                    buffer = io.BytesIO()
                    image.save(buffer, "PNG", exif=exif)
                path = self.archive({"1.png": buffer.getvalue()}, name=f"render{orientation}.cbz")
                self.assertTrue(convert(path).ok)
                rendered = subprocess.run(
                    ["pdftoppm", "-png", "-singlefile", "-r", "96", str(path.with_suffix(".pdf"))],
                    capture_output=True, check=True,
                )
                with Image.open(io.BytesIO(rendered.stdout)) as actual:
                    with Image.open(io.BytesIO(buffer.getvalue())) as source:
                        with ImageOps.exif_transpose(source) as expected:
                            self.assertEqual(actual.size, expected.size)
                            for x, y in ((2, 2), (expected.width - 3, expected.height - 3)):
                                self.assertEqual(actual.getpixel((x, y)), expected.getpixel((x, y)))
