<div align="center">

# CB2pdf

**Comics in. Verified PDFs out.**

Convert CBZ and CBR archives while preserving image quality and protecting your originals.

[![CI](https://github.com/empr0r/CB2pdf/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/empr0r/CB2pdf/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![Version](https://img.shields.io/badge/version-2.0.0-249b78)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[Quick start](#quick-start) · [Usage](#usage) · [RAR setup](#rar-setup) · [Documentation](#documentation)

</div>

## Why CB2pdf?

- **Preserve the pages.** Original resolution by default, with direct JPEG and compatible PNG embedding to avoid recompression.
- **Protect your library.** Originals stay put; existing PDFs are protected unless you explicitly request an overwrite.
- **Get the order right.** Natural sorting handles `page1`, `page2`, `page10` and nested chapters.
- **Handle more formats.** JPEG, PNG, WebP, BMP, GIF and TIFF, including animation frames and multipage images.
- **Choose the tradeoff.** Lossless, balanced and small profiles, plus optional resizing, DPI and page layout.
- **Convert a whole shelf.** Recursive discovery, bounded workers, dry runs and per-volume JSON reports.

## Quick start

Requires **Python 3.11+**. The validation matrix covers Python 3.11–3.14 on Linux, Windows and macOS.

```sh
git clone https://github.com/empr0r/CB2pdf.git
cd CB2pdf
python -m venv .venv
```

Activate the environment for your shell:

| Shell | Command |
|---|---|
| Linux / macOS | `source .venv/bin/activate` |
| Windows PowerShell | `.\.venv\Scripts\Activate.ps1` |

Then install and convert:

```sh
python -m pip install .
cb2pdf convert comic.cbz
```

The PDF is created alongside the archive. The original is kept. Use `python -m cb2pdf` if the console command is not on PATH.

For CBR files, complete the optional [RAR setup](#rar-setup) below.

## Usage

```sh
# Convert multiple volumes into one output directory
cb2pdf convert volume1.cbz volume2.cbr --output ./pdfs

# Convert a library, preserving its directory structure under ./pdfs
cb2pdf convert ./library --recursive --output ./pdfs --workers 2

# Inspect an archive or preview a batch
cb2pdf inspect comic.cbz
cb2pdf convert ./library --recursive --dry-run

# Create smaller pages or fit a fixed PDF layout
cb2pdf convert comic.cbz --quality small --jpeg-quality 80
cb2pdf convert comic.cbz --max-size 2560
cb2pdf convert comic.cbz --page-size a4 --dpi 300

# Archive originals after verified PDF creation
cb2pdf convert comic.cbz --move-original ./archive

# Save conversion details, including page transformations
cb2pdf convert ./library --report conversion.json --log-file conversion.log --json-logs
```

`--output` names a directory. Use `--overwrite` to explicitly replace an existing PDF after verification. Reports and file logs require unused filenames.

### Quality profiles

| Profile | Resolution | Encoding policy |
|---|---|---|
| `lossless` **(default)** | Original, unless resizing is requested | Preserve compatible JPEG/PNG streams; otherwise use lossless PDF encoding |
| `balanced` | Original, unless resizing is requested | JPEG quality 90 for opaque pages; preserve alpha losslessly |
| `small` | Fit within 1600 × 1600, unless overridden | JPEG quality 75 for opaque pages; retain alpha with the requested size |

Resizing changes pixels even with the `lossless` encoding profile. Lossy encoding does not guarantee a smaller file. Every transformation is recorded when you request a JSON report.

Transparency is preserved by default. Use `--flatten-alpha --background FFFFFF` to flatten onto white. Animated images and multipage TIFFs become one PDF page per frame/page; `--frames reject` refuses multiframe inputs. Animation timing does not carry over to PDF.

Run `cb2pdf convert --help` for every option, or see the [configuration guide](docs/configuration.md).

## RAR setup

CBZ conversion needs no external archive tool. CBR conversion needs the optional Python dependency **and** a compatible decoder on PATH:

```sh
python -m pip install '.[rar]'
```

| Platform | Decoder setup |
|---|---|
| Arch Linux | `sudo pacman -S unrar` |
| Debian / Ubuntu | `sudo apt install unar` |
| macOS with Homebrew | `brew install unar` |
| Windows | Install [7-Zip](https://www.7-zip.org/) and add the directory containing `7z.exe` to PATH |

UnRAR, unar, full 7-Zip and bsdtar have different capabilities. Some distribution 7-Zip builds omit RAR codecs; bsdtar cannot decode solid RAR4. Missing capabilities produce actionable errors. Encrypted, split/multivolume and self-extracting archives are unsupported. See [backend troubleshooting](docs/troubleshooting.md).

## Your files come first

Conversion writes a temporary PDF on the destination filesystem, verifies its structure and page completeness, and commits it only after success. Direct JPEG/PNG streams also receive SHA-256 checks to detect changed content or reordered pages. A required page failure prevents a partial PDF from being published.

Originals are kept by default. With `--move-original`, archival starts after PDF commit; archival failures retain the PDF and report the partial outcome. Exclusive publication requires filesystem hard-link support. Other filesystem, interruption and color/metadata limitations are documented in [troubleshooting](docs/troubleshooting.md).

## Performance, measured

The retained five-trial comparison measured **1.19×–1.99× faster medians** than the reference fork across five synthetic workloads where both produced complete, pixel-identical output. Large-JPEG peak memory fell from **417.4 to 268.5 MiB** against the pre-optimization implementation.

These are workload-specific historical measurements, not universal speed or memory guarantees. [Read the results](benchmarks/reports/performance-summary.md) and [reproduce the benchmarks](docs/performance.md).

## Documentation

| Guide | Contents |
|---|---|
| [Configuration](docs/configuration.md) | Flags, quality settings, resource limits and exit codes |
| [Troubleshooting](docs/troubleshooting.md) | RAR dependencies, unsupported inputs and recovery |
| [Architecture](docs/architecture.md) | Pipeline responsibilities and safety contracts |
| [Development](docs/development.md) | Tests, typing, formatting and package builds |
| [Performance](docs/performance.md) | Workloads, measurement policy and reproduction |
| [Release validation](docs/releasing.md) | Installed-artifact checks and platform evidence |
| [Changelog](CHANGELOG.md) | Version history and migration notes |

### Coming from the original script?

The installable CLI is the recommended workflow. The compatibility launcher remains: `python cb2pdf.py` without arguments scans its own directory and moves successfully converted archives into `old`. Install the package before copying the launcher elsewhere. Explicit CLI arguments also work through the launcher.

MIT licensed. Original copyright and the historical reference implementations' notices are preserved; see [LICENSE](LICENSE) and [benchmark references](benchmarks/reference/).
