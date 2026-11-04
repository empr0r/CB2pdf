# Performance follow-up

This report describes the optimization measurements at commit `fd1dc7f`.
It predates final CBR diagnostics and fresh dependency resolution. Current
platform qualification is recorded in [release validation](../../docs/releasing.md).

The optimized implementation completed every synthetic page with exact ordered
pixels in all five trials. It beat the retained fork's median conversion time
in all five synthetic workloads where the fork also produced complete,
pixel-identical output. Preservation, SHA-256 verification, independent PDF
parsing, fsync and exclusive publication remained enabled.

## Measured synthetic results

Times are median conversion seconds from five fresh-process trials per variant.
Baseline means the pre-optimization package at commit `c33c10b`.

| Workload | Baseline | Fork | Optimized | Fork / optimized, equivalent output |
|---|---:|---:|---:|---:|
| Small JPEG | 0.0532 | 0.0540 | 0.0427 | 1.27× |
| Large JPEG | 0.6006 | 0.5169 | 0.4351 | 1.19× |
| PNG-heavy | 0.1453 | 0.0875 | 0.0687 | 1.27× |
| Nested PNG | 0.0926 | 0.0626 | 0.0462 | 1.36× |
| Many small volumes | 0.0886 | 0.1536 | 0.0773 | 1.99× |
| Mixed format | 0.2121 | 0.1110 | 0.2013 | Excluded: fork has 5/6 pages, 2/6 exact |
| High resolution | 0.3900 | 1.8654 | 0.2506 | Excluded: fork resizes, 0/4 exact |
| Several large volumes | 0.7619 | 4.8120 | 0.5127 | Excluded: fork changes pixels, 0/24 exact |

The optimized median improved on the baseline in every synthetic workload,
from 1.05× for mixed formats to 2.12× for PNG-heavy input. Output byte counts
matched the baseline in every workload. These are observed medians on a shared
host, not confidence bounds or a universal speed guarantee.

Maximum observed worker RSS fell from **417.4 to 268.5 MiB** for large JPEGs
(35.7%) and **395.1 to 167.6 MiB** for several large volumes (57.6%). Small-JPEG
RSS was essentially unchanged (59.6 versus 59.9 MiB). Preserving the large-volume
images still uses more memory and output bytes than the fork's lossy output;
those are different preservation policies.

Large-JPEG median worker CPU time was 0.597 seconds before and 0.613 seconds
after optimization, while elapsed time decreased. The hashing helper spends
additional simultaneous CPU capacity: observed median CPU usage was about 139%
for optimized large JPEGs. This is a throughput/latency improvement, not a claim
of lower CPU cost in every workload. The helper is bounded to one thread and
two outstanding payloads per active archive. Default archive concurrency remains
one.

The raw synthetic record contains 120 trials; all 690 optimized page checks
passed. See [full table](performance-verified.md) and
[machine-readable measurements](performance-verified.json) for ranges, CPU,
temporary-space samples, output bytes and individual results.

## Private real-page fixtures

These are read-only CBZ fixtures previously exported from the user's image-only
PDFs, not original CBZ/CBR releases. Each variant receives owned input copies;
fixture SHA-256 identities were unchanged after the run. No private page content
is committed or uploaded.

| Fixture | Pages | Baseline seconds | Fork seconds | Optimized seconds | Optimized / fork peak RSS MiB |
|---|---:|---:|---:|---:|---:|
| 1 | 98 | 0.3589 | 0.2790 | 0.2510 | 131.3 / 223.0 |
| 2 | 184 | 0.2722 | 0.2063 | 0.2127 | 99.0 / 159.7 |
| 3 | 183 | 2.2891 | 1.5402 | 1.4326 | 122.5 / 146.7 |

All optimized pages were exact in all five trials: 2,325 page comparisons.
Baseline/current output byte counts matched for every fixture. The first
fixture's optimized median was 1.11× faster than the fork. The second retained
a **6.4 ms (3.1%) fork median advantage**: the trial ranges overlap
(optimized 197.7–227.4 ms; fork 194.9–211.6 ms). This is effectively a close race,
with optimized RSS about 38% lower. It does not establish an across-the-board
real-content speed win.

For fixture 3, the fork preserved only 3/183 pages' pixels; the optimized output
preserved all 183. Its raw runtime advantage therefore is not an equal-quality
encoder comparison. Relative to the baseline, optimized real-fixture medians
improved 1.28×–1.60×. The final synthetic and real records together contain 165
trials and **3,015 exact optimized page comparisons**, including repeats.
See [real results](performance-verified-real.md) and
[raw record](performance-verified-real.json).

## Engineering changes and safeguards

- `png.py` collects metadata through Pillow's chunk parser without constructing
  a raster. CRC, bounded zlib/checksum completion, scanline extent/filter tags,
  text/ICC limits and cancellation remain checked. Interlace, alpha and animation
  retain decoding where needed. Late color/layout metadata fails explicitly;
  late EXIF remains a compatibility feature.
- `images.py` reuses already-inspected orientation and skips a redundant reopen
  only for Pillow's inherited no-op verifier. Dedicated plugin verifiers remain.
  Single-frame APNGs take the frame normalization path.
- `archives.py` removes intermediate ZIP growth/copy buffers while retaining
  member-size, actual-size, aggregate, CRC and cancellation checks.
- `digests.py` overlaps large native SHA-256 work with document I/O. Inputs below
  256 KiB stay synchronous; failures and every digest are awaited before success.
- `pdf.py` owns and releases the internal writer graph before independent
  verification, including failed writes. Small PDFs use read-only mapped parsing
  with a file-read fallback. Rotations are independently checked. There is no
  unconditional garbage collection, raster cache or library-global patch.

The suite increased from 81 to 107 tests, including invalid inner PNG compression
with correct outer CRCs, decompression bounds, late metadata, APNG, all rotations,
hash failures, reordered streams, mapping failure, dedicated plugin verification,
and actual graph release with automatic garbage collection disabled. Existing
data-safety, fault-injection, security and pixel tests remain.

## Reproduction and limits

See [methodology and commands](../../docs/performance.md#performance-follow-up).
The baseline source SHA-256 is
`ac37d8753c63e8b5db7df4a28edbefc71f4a65cbe1754af016056e1d3a10723f`;
the measured optimized source is
`1a2ca6f8082b3491a96fd388ea48729fd81d73de98dd5aad8275b0d0e5d8ab66`.
Each final record confirms one consistent source version per variant.

Measured here: Linux x86-64, CPython 3.14.9, Ryzen 7 3800X, approximately
31.3 GiB RAM, Pillow 13.0.0, img2pdf 0.6.3 and pypdf 6.12.0. Dependencies were
loaded from upstream source locally. The fork runs unchanged with its default
extraction, PDF buffering, garbage collection and move-original workflow on
owned input copies. The baseline/current runs keep their preservation defaults.
Pikepdf was absent, so the fork used
img2pdf's internal engine. Cache state was warm; imports and external decoded
pixel assessment were excluded from conversion timing. Whole-process wall
time is recorded separately. Temporary-space sampling every 5 ms gives lower
bounds, not total I/O volume.

The existing original-script comparison remains in `comparison.json`; this
follow-up measures the previous redesign against the optimization and fork.
Superseded development reports are indexed in [the report archive](README.md).
Other platforms/runtimes, pikepdf, compressed CBR throughput, cold-cache behavior
and hard memory/time isolation remain unmeasured. Later cross-platform
correctness runs passed; those do not establish cross-platform performance.

## Validation at the measured revision

- 107 unit/integration/regression/security tests passed with no skips or failures,
  including independent Poppler rendering of all eight orientation modes.
- Mypy checked all 17 package modules; pyflakes, pycodestyle, autopep8,
  compileall, Python 3.11 grammar parsing (31 files) and Git whitespace checks
  passed. Grammar checking does not establish a Python 3.11 runtime test.
- Wheel and source distribution built through the setuptools PEP 517 backend.
  The new adapters and tests were present; private fixture paths/content were
  excluded. The wheel installed offline into an isolated environment and its
  actual installed CLI passed `--version` and a six-page self-benchmark with
  exact pixels and original JPEG streams. See
  [archived installed-wheel record](https://github.com/empr0r/CB2pdf/blob/362900da51e1019c968c9e3bd1677e9c4c853837/benchmarks/reports/performance-wheel-smoke.json).
- All original JPEG streams were byte-identical in every optimized comparison
  trial. All required page/pixel checks passed; baseline/current output sizes
  matched. Fixture input hashes were unchanged.
- Summary generation reproduced the final synthetic table and exposed differing
  per-trial fidelity counts in a controlled check rather than displaying only
  the first trial.

The remaining performance work should start with the near-tied 184-page fixture,
independently installed pikepdf/backends, platform measurements and compressed
RAR workloads. Hard native memory/time isolation still requires a separate
process design; this change does not claim it.
