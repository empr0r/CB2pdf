# CB2pdf

**2.0.0 — release preparation.** The rc2 implementation passed all 16 platform/dependency CI configurations. The stable-version artifacts receive a final validation run before publication. See the [release procedure](docs/releasing.md).

Convert CBZ/ZIP and CBR/RAR comic archives into complete, verified PDFs. The default preserves resolution, avoids lossy image recompression, and keeps original archives. Existing outputs are protected unless `--overwrite` is explicitly supplied.

## Installation

Python 3.11 or newer is required. Fresh installed-wheel tests pass locally on Linux with Python 3.11–3.14, latest dependencies, and the minimum runtime dependencies on Python 3.11. Sixteen CI configurations cover those runtimes plus dependency-floor checks on Linux, Windows and macOS; remote results are pending.

```sh
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
python -m pip install .
# Optional RAR support
python -m pip install '.[rar]'
```

RAR also requires a compatible executable on PATH: `unrar`, `unar`, `7z`, or `bsdtar`. On Arch Linux, install `unrar` with `sudo pacman -S unrar`. On Debian/Ubuntu, `sudo apt install libarchive-tools` provides bsdtar. On macOS, try the system bsdtar or install unar. On Windows, add the folder containing UnRAR.exe or 7z.exe to PATH. UnRAR and 7-Zip pass the included compressed/solid RAR4/RAR5 fixtures on Linux. Bsdtar passes ordinary RAR4 and ordinary/solid RAR5; solid RAR4 requires another decoder and produces an actionable error.

The runtime uses Pillow, img2pdf, and pypdf. The img2pdf distribution also depends on pikepdf; CB2pdf intentionally selects img2pdf's internal writer for consistent behavior across environments. No external PDF renderer is needed for conversion.

## Usage

```sh
cb2pdf convert comic.cbz
cb2pdf convert comic.cbr another.cbz --output ./pdfs
cb2pdf convert ./library --recursive --workers 2
cb2pdf convert comic.cbz --quality balanced
cb2pdf convert comic.cbz --quality small --jpeg-quality 80
cb2pdf convert comic.cbz --max-size 2560
cb2pdf convert comic.cbz --page-size a4 --dpi 300
cb2pdf convert comic.cbz --keep-original
cb2pdf convert comic.cbz --move-original ./archive
cb2pdf convert comic.cbz --dry-run
cb2pdf convert ./library --report conversion.json --log-file conversion.log --json-logs
cb2pdf inspect comic.cbz
cb2pdf benchmark --quick --trials 3 --output benchmark-results.json
cb2pdf --version
```

Use `python -m cb2pdf` if the console command is not on PATH. `--output` names a directory; recursive conversion preserves the input directory structure beneath it. Multiple roots that would produce the same output are rejected before conversion. Individual files are identified by signature, so a ZIP mislabeled `.cbr` is accepted. Directory discovery selects `.cbz` and `.cbr` filenames.

Profiles:

| Profile | Resolution | Encoding |
|---|---|---|
| `lossless` (default) | Original unless resizing explicitly requested | Direct JPEG/compatible PNG streams; otherwise lossless PDF encoding |
| `balanced` | Original unless resizing explicitly requested | JPEG quality 90 for opaque images; alpha preserved losslessly |
| `small` | Fit within 1600×1600 unless overridden | JPEG quality 75 for opaque images; alpha preserved with the requested size |

Explicit resizing changes pixels, including when combined with the `lossless` encoding profile. Lossy profiles can increase some files' sizes. Every normalization, resize, and JPEG encoding appears in the JSON conversion report. Transparency is preserved unless `--flatten-alpha` is selected; `--background FFFFFF` sets the flattening color.

JPEG, PNG, WebP, BMP, GIF, and TIFF are supported. Every animation frame or TIFF page becomes a PDF page, in frame order. `--frames reject` refuses multiframe input instead. Animation timing does not carry over to PDF. Visible image members are naturally sorted by directory components and numeric runs. Hidden paths, AppleDouble files, and `__MACOSX` are ignored.

## File safety

Conversion writes an exclusive temporary on the destination filesystem, fsyncs it, parses the finalized PDF, checks page completeness and image resources, then commits it. Direct JPEG and compatible PNG streams are also checked against per-page SHA-256 digests, detecting changed streams or page reordering. Other formats receive structural verification and have pixel-fidelity integration coverage.

No-overwrite publication uses an exclusive hard link; unsupported filesystems fail safely. Explicit overwrites use atomic replacement after verification. Originals move only after successful PDF commit. Archival copies are committed exclusively and synced before removal of the source name. Copy or removal failures retain the PDF and report an incomplete archival outcome. Cross-filesystem archival was verified locally using a generated archive on distinct `/tmp` and project filesystems; Windows behavior remains unverified.

Catchable failures clean only temporaries owned by that conversion. A killed process can leave `.cb2pdf-*.cb2pdf-part` files; investigate those individually. Atomic publication is not a transaction spanning PDF and source archival, and Windows lacks a portable directory-fsync operation.

## Legacy workflow

Running `python cb2pdf.py` without arguments scans the launcher's directory and moves successfully converted originals to its `old` folder. Install the package before copying the launcher elsewhere. The original single-file-only installation is superseded by this package. Explicit CLI arguments work through the launcher too. Importing the application no longer starts conversions or creates folders.

## Development and further details

```sh
python -m pip install -e '.[rar,dev,benchmark]'
python -m unittest discover -v
python -m mypy
python -m pyflakes src tests tools benchmarks/compare.py benchmarks/real_world.py benchmarks/performance.py cb2pdf.py
python -m pycodestyle --max-line-length=100 src tests tools benchmarks/compare.py benchmarks/real_world.py benchmarks/performance.py cb2pdf.py
python -m autopep8 --recursive --diff --exit-code --max-line-length=100 src tests tools
python -m build
python benchmarks/compare.py --trials 3 --workers 1 2 4
```

The 119-test unittest suite uses real archives/PDFs and injected filesystem failures. Poppler's optional `pdftoppm` enables additional rendering checks. RAR tests skip when the optional library or backend is unavailable.

See [configuration](docs/configuration.md), [architecture](docs/architecture.md), [troubleshooting and limitations](docs/troubleshooting.md), [performance methodology](docs/performance.md), [initial assessment](docs/assessment.md), and [changelog](CHANGELOG.md). Measured comparisons are in [benchmarks/reports](benchmarks/reports/).

MIT licensed; the original copyright is preserved. Historical fork snapshots carry their own notices in [benchmarks/reference](benchmarks/reference/).

## Performance follow-up

The optimized pipeline retains fsync, strict independent PDF parsing, direct-image stream SHA-256 checks and lossless defaults. It removes avoidable PNG pixel reconstruction, validates opaque PNG DEFLATE/scanline structure in bounded buffers, reads ZIP members without intermediate growth buffers, overlaps large hashes with I/O, and releases the writer's cyclic image graph before verification. One active archive can use one additional hashing thread, with two outstanding payloads at most; small hashes run synchronously.

In five-trial fresh-process tests, the optimized version beat the reference fork's median conversion time in all five workloads where both produced complete pixel-identical output (1.19×–1.99×). This is a measured workload-specific result, not a universal speed claim. The mixed-format fork output remains incomplete/lossy and is excluded from equivalent-output rankings. See [performance report](benchmarks/reports/performance-summary.md) and [methodology](docs/performance.md#performance-follow-up).
