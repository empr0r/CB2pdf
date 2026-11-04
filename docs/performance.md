# Performance methodology

The [retained performance summary](../benchmarks/reports/performance-summary.md)
interprets the final optimization measurements. The [report index](../benchmarks/reports/README.md)
separates those results from the earlier original/fork/redesign comparison.
JSON files are the measurement record: check source identities, errors,
completeness and fidelity before comparing speed. Smaller lossy output is not
evidence of better preservation.

## Reproduce comparisons

Install development and benchmark dependencies:

```sh
python -m pip install -e '.[rar,dev,benchmark]'
```

Compare the original script, reference fork and current implementation:

```sh
python benchmarks/compare.py --trials 3 --workers 1 2 4 --output benchmarks/reports/new-comparison.json
```

### Performance follow-up

Compare the frozen pre-optimization package, current package and retained fork:

```sh
git worktree add --detach ../cb2pdf-performance-baseline c33c10b
python benchmarks/performance.py --baseline-src ../cb2pdf-performance-baseline/src --trials 5 --output benchmarks/reports/new-performance.json
```

Trials run in a randomized order, each in a fresh process. Source SHA-256
identities are recorded per trial; a mixed-version run cannot produce a summary.
The optional `--fixture-dirs /path/to/fixture1 /path/to/fixture2` accepts prepared
static-page CBZ fixture directories. Each variant receives its own input copies
in an application-owned temporary directory, so historical code can move only
those copies. Custom dataset labels are anonymized.

For an installed-package smoke benchmark:

```sh
cb2pdf benchmark --quick --trials 3 --output new-smoke.json
cb2pdf benchmark --trials 3 --workers 2 --output new-benchmark.json
```

## Workloads and quality checks

Eight synthetic workloads cover small/large JPEGs, PNGs, mixed
JPEG/PNG/WebP/BMP/GIF/TIFF, 3000 × 4500 scans, nested paths, twelve small volumes
and three large volumes. A fixed seed generates textured images from noisy tiles.
This is reproducible but does not represent every scan's compression properties.
Unpadded page numbers exercise natural ordering; ZIP members use stored encoding.
Dimensions are recorded in `benchmarks/compare.py`.

Every output page is checked for count, order and decoded RGBA equality outside
the timed region. JPEG comparison decodes the actual embedded DCT stream;
exporting through pypdf can recompress it and is not a valid fidelity comparator.
Original JPEG byte-stream matches are recorded separately. Historical return
code zero does not establish successful conversion. In mixed-format input, the
original script selects only JPEG/PNG and the fork omits `.tif`; incomplete or
changed-pixel output is excluded from equivalent-output speed rankings.

The original script's artificial batch sleeps are set to zero; its batch/GC
behavior otherwise remains. The fork remains sequential and retains extraction,
PDF buffering, GC and source moves on owned copies. Original/fork defaults can
be lossy; the redesign retains its preservation, verification and fsync defaults.
These are observable pipeline comparisons, not equal-quality encoder rankings
unless the independent fidelity checks establish equivalent output.

## Metrics and measurement limits

- Conversion wall time excludes imports, fixture setup and external fidelity
  assessment. It includes the requested conversion, verification and commit work.
  Whole-process wall time is recorded separately.
- Linux peak worker RSS uses `/proc/self/status` VmHWM after conversion, including
  imports. An early harness's inherited getrusage high-water marks were invalid
  and discarded. Other POSIX systems use getrusage and require independent
  inheritance verification; Windows RSS/CPU metrics are null.
- Worker CPU seconds and utilization are recorded where available. Native decoder
  subprocess CPU is not included.
- Temporary logical bytes are sampled every 5 ms, including destination
  `.cb2pdf-part` files. These are lower bounds, not total writes or exact disk use.
- The host is shared, caches are warm and background activity can affect results.
  Repeated trials expose variability; these are not isolated lab measurements.

The recorded optimization run measured commit `fd1dc7f` against baseline
`c33c10b`: 120 synthetic trials and 45 real-fixture trials, with 3,015 exact
optimized page comparisons including repeats. The original three-way comparison
has 72 trials. Exploratory runs are archived through the report index.

The host was Linux x86-64, Ryzen 7 3800X (8 cores / 16 logical CPUs), about
31.3 GiB RAM and CPython 3.14.9. Pillow 13.0.0, img2pdf 0.6.3 and pypdf 6.12.0
were loaded from inspected upstream source because index downloads were blocked
at measurement time. Pikepdf was absent, so the fork used img2pdf's internal
engine. Later fresh-install validation succeeded through ordinary package-index
resolution; those dependency combinations have not been performance-ranked.

These timings predate final CBR diagnostics and dependency updates. They do not
establish current performance on Windows/macOS, with pikepdf, on cold caches or
for compressed CBR workloads. Cross-platform correctness is separately recorded
in [release validation](releasing.md).

## Private real-page fixtures

The image-only PDF exporter preserves embedded JPEG streams and writes other
images as lossless PNG before creating CBZ fixtures:

```sh
python benchmarks/real_world.py /path/to/volume1.pdf /path/to/volume2.pdf --trials 3 --work benchmarks/work/private-run --output benchmarks/reports/private-run.json
```

Source PDFs are hashed before and after preparation. Generated fixtures stay in
the ignored work directory; reports contain anonymous labels and hashes, not
private manga pages. This tests exported page content, not original archive
structure or source PDF layout/text.

Recorded fixtures have 98, 184 and 183 pages. Their source hashes remained
unchanged. The third PDF needed recovery for missing ASCIIHex end markers;
warning counts remain in `real-world.json`. Indexed palettes are exported
explicitly, with a regression test and an independent Poppler check on one page.
This does not establish equivalent rendering of every original PDF page.

## Optimizations and resource boundaries

- PNG metadata inspection avoids raster reconstruction while retaining CRC,
  bounded DEFLATE/checksum completion, scanline/filter and text/ICC checks.
  Compressed slices are at most 64 KiB; opaque output blocks are at most 1 MiB.
  Alpha, interlace and animation decode when required. Late EXIF is accepted;
  malformed late color/transparency/DPI chunks fail. See the
  [PNG chunk-order specification](https://www.w3.org/TR/png-3/#5ChunkOrdering).
- Already-inspected orientation passes through owned img2pdf page handles;
  output rotations are independently verified. Pillow plugins with dedicated
  verifiers retain a fresh read; the inherited no-op verifier can reuse inspection.
- ZIP reads avoid intermediate growth/copy buffers while retaining CRC,
  declared/actual extent, aggregate-budget and cancellation checks. RAR uses
  incremental reads.
- SHA-256 can overlap I/O: one helper thread and at most two outstanding payloads
  per stage, with inputs below 256 KiB processed synchronously. Every future is
  awaited. Reduced wall time can use more instantaneous CPU capacity.
- The owned PDF writer graph is released before independent verification,
  including on failed writes. PDFs up to 16 MiB can use mapped reads, with an
  ordinary-read fallback. There is no unconditional GC or raster cache.

`img2pdf` outputstream avoids a second complete PDF byte string but retains
compressed image objects. Processing is not constant-memory. Configured budgets
bound inputs and concurrency, not native allocator behavior. One archive worker
is the default; choose more from workload measurements. Multiprocessing and hard
OS memory/time isolation are not implemented. Compressed CBR throughput and
broader color/high-depth corpora remain useful follow-up work.
