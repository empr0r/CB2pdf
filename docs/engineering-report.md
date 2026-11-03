# Operation Cóndor engineering report

## Delivery and repository provenance

The implementation is in `/home/empr0r/Projects/CB2pdf`, branch `operation-condor`. The unrelated older checkout in `Documents/GitHub/CBZ-to-pdf` remains untouched. Direct Git/pip networking was unavailable, so the requested public upstream was imported through the GitHub connector as local snapshot commit `2ec28de`, based on reviewed upstream head `19bc5a2`. This is explicitly a source snapshot, not a complete remote Git clone. Implementation commit: `796a341`.

No remote writes, pushes, publication or releases were performed. The original MIT copyright remains in LICENSE; reference fork notices remain beside the retained benchmark snapshot. Historical reference formatting is intentionally excluded from whitespace checking rather than rewritten. All private manga fixtures and generated PDFs are ignored and excluded from the source distribution.

## Architecture and implemented functionality

Fifteen typed package modules establish clear boundaries: configuration/domain/error models; signature-driven archive reading and resource checks; natural ordering; image inspection and lazy normalization; PDF embedding and independent verification; filesystem transactions; single-file orchestration; bounded batch scheduling; logging/reporting; CLI; and reproducible benchmark support. The package has a console entry point, module entry point, public conversion API and legacy launcher.

Completed capabilities include ZIP/CBZ and optional RAR/CBR processing, nested/Unicode paths, natural and lexical ordering, six image-format families, multiframe expansion/rejection, all eight EXIF orientations, CMYK/grayscale/indexed/alpha handling, ICC preservation where supported, optional resizing/upscaling, three explicit quality profiles, DPI/fixed-page layout, metadata, batch/recursive input, output directories, worker limits, memory estimates, fail-fast cancellation, dry-run, inspection, JSON results/logs, progress and useful exit codes.

The architecture and configuration documents describe contracts and exact policies. This is a substantial package replacing the script's internal functions while preserving the script-launch workflow; it is not a condensation refactor. The obsolete batching sleeps and unconditional garbage collection were removed as undocumented performance assumptions, not replaced with claims of constant memory.

## Preservation and data safety

Default conversion keeps originals, preserves original resolution and retains JPEG/compatible PNG compressed image streams. Necessary normalization uses lossless encoding; lossy JPEG and resizing require explicit profile/options and are reported per page. Animation frames are never silently discarded. Unsupported samples and invalid required pages fail the document.

Output is generated in a uniquely owned target-filesystem temporary, synced, parsed strictly and checked for completeness, dimensions and resources before publication. Direct JPEG and compatible PNG streams receive independent SHA-256 verification in page order. Existing output is protected by exclusive hard-link publication; explicit overwrite uses verified atomic replacement. A PDF commit and source archival are distinct transactions with accurate partial statuses.

Archival copies/commits/syncs the original before removing its old name and never overwrites an archival destination. A generated archive was successfully moved between distinct Linux filesystems (device IDs 39 and 47) with identical SHA-256 bytes. Mutation, collision, verification, write, interruption and sync failures retain appropriate source/output states. The final cleanup review also ensures temporary unlink is attempted when buffered close raises.

No source manga PDF was modified. Before/after SHA-256 values for all three real-content sources match in the recorded report.

## Measured performance

Primary comparison: 72 trials, eight workloads, three implementations, three trials each, one worker. Hardware: AMD Ryzen 7 3800X, 16 logical CPUs, about 31.3 GiB RAM, Linux x86-64. Software: CPython 3.14.9, Pillow 13.0.0, img2pdf 0.6.3, pypdf 6.12.0; rarfile 4.2 for archive tests. Dependencies were loaded from inspected source. pikepdf was absent, so the fork's automatic engine selected the internal writer; this is an explicit portability limit of the comparison.

Selected median conversion seconds:

| Workload | Original | Fork | Redesign | Preservation/completeness |
|---|---:|---:|---:|---|
| Small JPEG | 0.1459 | 0.0561 | 0.0467 | Redesign/fork retain 12/12 pages' decoded pixels; original recompresses |
| Large JPEG | 2.1699 | 0.4962 | 0.5872 | Redesign/fork retain 24/24; new verification costs time |
| PNG-heavy | 0.1676 | 0.0932 | 0.1463 | Redesign/fork retain 8/8; original changes pixels |
| High-resolution | 1.2748 | 1.8424 | 0.3834 | Only redesign retains original decoded pixels on all four scans |
| Mixed formats | 0.0634 | 0.1114 | 0.2108 | Original 2/6 pages, fork 5/6, redesign 6/6 with exact decoded pixels |
| Several large volumes | 2.6254 | 4.6107 | 0.7758 | Redesign retains 24/24 pixels; historical outputs are lossy |

The redesign is not universally faster or lower-memory. In the large-JPEG workload maximum worker RSS was 391.0 MiB versus original 408.7 and fork 486.3 MiB. In several-large-volumes it was 393.5 MiB versus original 203.2 and fork 145.6 MiB, with very different retained quality/output sizes. PNG-heavy RSS was 47.7 MiB versus original 95.8 and fork 64.9 MiB. img2pdf retains compressed document objects; outputstream avoids an additional whole-document bytes object but does not make processing constant-memory.

Private real-page round trips (three trials each):

| Anonymous fixture | Pages | Median seconds | Maximum RSS MiB | Exact ordered pixels per trial |
|---|---:|---:|---:|---:|
| Real volume 1 | 98 | 0.3558 | 217.4 | 98/98 |
| Real volume 2 | 184 | 0.3077 | 155.7 | 184/184 |
| Real volume 3 | 183 | 2.3130 | 190.7 | 183/183 |

There were no conversion or validation errors in these nine trials: 1,395 checked output pages, representing 465 distinct fixture pages. The fixtures were derived from already-converted PDFs, not original CBZ/CBR archives. One source had 179 recoverable missing-ASCIIHex-EOD warnings. Its indexed palette required explicit fixture export; a regression test and an independent exact Poppler pixel check on one page validate that path. This does not claim every original PDF rendering/layout was reproduced.

The source digest in each benchmark record identifies the measured version. A later cleanup-only failure-path fix is documented separately; successful conversion logic is unchanged and a three-trial final-source smoke benchmark passes. An additional 168-trial scaling exploration is retained with explicit shared-host/version caveats; it is not used for the primary comparisons. Process-based scheduling was not benchmarked.

## Validation

- **81 unittest tests passed, no local skips or failures.** Tests use actual ZIP/RAR archives and PDFs, compressed-stream and pixel comparisons, a real indexed-ASCIIHex fixture, hostile names/duplicates/links/limits, atomic races, source mutation and targeted fault injection. Eight EXIF modes were also rendered using Poppler.
- **mypy 1.18.2:** no issues in 15 package modules, targeting Python 3.11. External numpy stubs are skipped because the local future numpy uses Python 3.12-only syntax; application typing is checked.
- **pyflakes 3.4.0, pycodestyle 2.14.0, autopep8 2.3.2:** passed on maintained source/tests/runners. Historical benchmark snapshots are intentionally preserved and excluded.
- Compileall and Python 3.11 grammar parsing passed. This is syntax evidence, not a Python 3.11 runtime test.
- Wheel/sdist built through the setuptools PEP 517 backend. Offline editable installation and an isolated wheel installation succeeded. The installed wheel's CLI version and self-benchmark passed. Marker/manifest inspection confirmed typed package data, test helpers and exclusion of private fixtures.
- Poppler pdfinfo independently accepted the 98-, 184- and 183-page real-content outputs (PDF 1.3/1.4). An independent Poppler image extraction matched a real indexed grayscale source page exactly.
- One hundred controlled invalid-image conversions left file-descriptor counts unchanged (4 before and after).
- Cross-filesystem archival checksum checks passed on Linux. Normal network-resolved dependency installation could not be exercised because shell networking was blocked; dependencies were retained privately inside the ignored local virtual environment.

## Compatibility and remaining limitations

Verified locally: Linux x86-64, Python 3.14.9, the source versions above, stored RAR3, standard ZIPs, Poppler readability/rendering, offline package installation and distinct-filesystem archival. Twelve CI configurations cover Linux/Windows/macOS and Python 3.11–3.14, but no remote CI run or other local runtime platform is claimed.

Important remaining work includes compressed/solid RAR5 and backend diversity tests, a broader preservation corpus (especially unusual high-depth alpha/TIFF/ICC/gamma cases), Windows filesystem validation, extreme-size PDF tests, and evaluation of process isolation for hard native time/memory limits. Current cancellation is cooperative; native decoding and RAR subprocess reads can delay it. Limits and worker estimates are not an OS sandbox. Some source metadata, gamma semantics and animation timing do not map to PDF equivalently. No standalone executable is distributed.

The repository remains dependent on filesystem support for hard links and fsync semantics. SIGKILL/power loss can leave identifiable owned temporaries. Adversarial concurrent replacement of user-controlled filesystem entries is outside the transaction guarantees.

## Recommended next work

1. Run the configured platform matrix and expand compressed RAR/backend fixtures.
2. Validate difficult preservation cases against independent renderers and color-managed readers.
3. Benchmark the same lossless corpus with ordinarily installed pikepdf and prototype isolated process workers for enforceable memory/time bounds.
4. Improve large-document compressed-object lifecycle only after profiling; retain current honest memory accounting and verification.
5. Evaluate executable distribution after backend and platform validation, without remote publication until authorized.

See `benchmarks/reports/comparison.json`, `comparison.md`, `real-world.json`, `final-smoke.json` and `scaling-exploration.json` for measured evidence. Final local commits and working-tree status are reported in the delivery message; build products, validation dependencies and private fixtures remain ignored local artifacts.
