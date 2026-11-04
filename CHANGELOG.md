# Changelog

## 2.0.0rc2 — CI decoder compatibility (unpublished)

- Added per-archive inspection of enabled 7-Zip RAR codecs. Distribution builds missing a required method now report a dependency error rather than a misleading corruption failure. Queries have a finite timeout.
- Backend tests compare capability declarations with real native extraction of valid RAR4/RAR5 fixtures. Available methods still require exact output; unavailable methods must preserve the source and fail clearly. Added three parser regressions (119 tests total).
- CI result JSON records 7-Zip codec profiles, failure excerpts appear in console logs, and artifact uploads include only the current job report/log.
- Initial rc1 CI: build/quality, five Windows configurations and Linux basic passed. Ten Linux/macOS configurations exposed stripped 7-Zip codecs; rc2 requires another platform run before release.

## 2.0.0rc1 — Release candidate (unpublished)

- Validated fresh installed wheels on Linux/Python 3.11–3.14 and the minimum supported runtime dependencies on Python 3.11.
- Added actual compressed/solid RAR4/RAR5 fixtures and native decoder coverage. Corrected bsdtar argument ordering without global patches; unsupported solid RAR4 reports the required alternative decoder.
- Added installed-wheel provenance checks, isolated test staging, CLI smoke tests, JSON evidence and a 16-configuration CI matrix testing shared build artifacts.
- Corrected the output-collision test to use distinct input directories on case-insensitive filesystems. The suite now contains 116 tests.

### Performance follow-up

- Added PNG chunk inspection that avoids pixel reconstruction while retaining CRC, DEFLATE checksum, scanline extent/filter and text-decompression validation. Late EXIF/XMP compatibility remains supported; invalid late color/transparency/DPI chunks fail explicitly.
- Reused validated per-page rotations through the owned img2pdf document, with independent output rotation checks. Single-frame APNGs normalize through Pillow rather than being mistaken for ordinary PNGs.
- Removed intermediate ZIP member growth buffers; added bounded SHA-256 overlap with I/O and a measured 256 KiB asynchronous threshold. All expected and output digests are awaited.
- Released img2pdf page-tree cycles after writing, including failures, before independent verification. Small PDFs can use mapped read-only parsing with a portable file-read fallback.
- Expanded the suite from 81 to 107 tests. Added randomized comparisons against a frozen pre-optimization package and the reference fork, plus private-fixture support. No validation/durability switches or lossy defaults were introduced.

### Engineering overhaul

- Introduced a typed, installable Python package and argparse conversion, inspection and benchmark commands.
- Protected existing PDFs by default; added verified atomic publication, direct-stream/page-order digests, safe source archival and truthful partial-outcome reporting.
- Preserved JPEG/compatible PNG representation and original resolution by default. Added conditional lossless normalization, alpha/orientation handling, frame expansion, explicit quality/resizing/layout policies and optional PDF metadata.
- Added signature-driven ZIP/RAR readers, deterministic natural ordering, unsafe-member rejection, metadata/size/ratio/pixel/page/document limits and bounded worker scheduling.
- Added JSON reports/logs, progress, exclusive sidecars, cancellation, dry-run, Python API, source-compatible launcher workflow and documented migration from single-file installation.
- Added real archive/PDF regression/security/failure tests, optional rendered-orientation checks, synthetic historical comparison infrastructure, private real-page validation, packaging checks and a cross-platform CI matrix.
- Default CLI source policy is now keep-original. The no-argument legacy launcher explicitly retains move-to-old behavior. No page-skipping success mode is provided.

## Original script

MIT-licensed CBZ/CBR conversion, four-worker batches, Pillow PDF output, progress and move-to-old workflow. The exact reviewed upstream and fork snapshots are retained for benchmarking with their notices.
