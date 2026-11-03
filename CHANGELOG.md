# Changelog

## 2.0.0 — Engineering overhaul

- Introduced a typed, installable Python package and argparse conversion, inspection and benchmark commands.
- Protected existing PDFs by default; added verified atomic publication, direct-stream/page-order digests, safe source archival and truthful partial-outcome reporting.
- Preserved JPEG/compatible PNG representation and original resolution by default. Added conditional lossless normalization, alpha/orientation handling, frame expansion, explicit quality/resizing/layout policies and optional PDF metadata.
- Added signature-driven ZIP/RAR readers, deterministic natural ordering, unsafe-member rejection, metadata/size/ratio/pixel/page/document limits and bounded worker scheduling.
- Added JSON reports/logs, progress, exclusive sidecars, cancellation, dry-run, Python API, source-compatible launcher workflow and documented migration from single-file installation.
- Added real archive/PDF regression/security/failure tests, optional rendered-orientation checks, synthetic historical comparison infrastructure, private real-page validation, packaging checks and a cross-platform CI matrix.
- Default CLI source policy is now keep-original. The no-argument legacy launcher explicitly retains move-to-old behavior. No page-skipping success mode is provided.

## Original script

MIT-licensed CBZ/CBR conversion, four-worker batches, Pillow PDF output, progress and move-to-old workflow. The exact reviewed upstream and fork snapshots are retained for benchmarking with their notices.
