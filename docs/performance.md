# Performance methodology

Use the JSON results as the measurement record. The Markdown comparison table reports median conversion time across repeated trials, maximum observed worker RSS, output bytes, completeness and exact decoded-pixel counts in expected page order. Smaller lossy output is not evidence of better preservation.

```sh
python -m pip install -e '.[rar,dev,benchmark]'
python benchmarks/compare.py --trials 3 --workers 1 2 4 --output benchmarks/reports/new-comparison.json
cb2pdf benchmark --quick --trials 3 --output new-smoke.json
# Larger installed self-benchmark
cb2pdf benchmark --trials 3 --workers 2 --output new-benchmark.json
```

Eight synthetic workloads cover small/large JPEGs, PNGs, mixed JPEG/PNG/WebP/BMP/GIF/TIFF, 3000×4500 scans, nested paths, twelve small volumes and three large volumes. A fixed seed generates textured images from noisy tiles; this makes fixtures reproducible but does not represent every real scan's compression characteristics. Unpadded page numbers exercise ordering. ZIPs use stored members, so archive recompression is not a confounder. Workload dimensions are recorded in `benchmarks/compare.py`.

Each trial runs in a fresh Python child process against identical fixtures. Preparation and external fidelity assessment are outside conversion time. Historical snapshots execute only in application-owned temporary directories. Original artificial batch sleeps are set to zero; its batch/GC logic otherwise runs. The fork remains sequential. New conversion includes its verification and fsync overhead. Original/fork defaults are lossy in different circumstances; the redesign uses preserve defaults. The comparison is therefore about observable correctness, fidelity, resource costs and throughput, not equal-quality encoder rankings.

Metrics:

- Conversion wall time excludes imports/setup and includes requested pipeline/commit work. Process wall time also includes startup and the sampling wrapper.
- Linux peak RSS is `/proc/self/status` VmHWM from the worker after conversion, including imports. An initial harness used inherited getrusage high-water marks; those invalid results were discarded. Other POSIX systems fall back to getrusage and need independent verification of inheritance behavior; Windows RSS/CPU metrics are null.
- Worker CPU seconds and percentage are recorded where resource is available. External decoder child CPU is not included.
- Temporary logical file bytes are sampled every 5 ms, including target-filesystem `.cb2pdf-part` files. Samples are lower bounds, not write-volume or exact disk-space measurements.
- All output pages are checked for count, natural order and decoded RGBA equality. JPEG comparison decodes the actual embedded DCT stream; exporting JPEG through pypdf can recompress it and is not a valid fidelity comparator. Exact original JPEG stream counts are recorded separately.
- Fixture preparation, validation and output deletion are not included in conversion time. The host is shared, caches are not flushed, and background activity may affect results. Repeated trials expose variability; these are not isolated laboratory measurements.

Read the `returncode`, validation errors and completeness fields before comparing speed. Historical return code zero does not prove successful conversion. In the mixed fixture, upstream selects only JPEG/PNG and the fork omits `.tif`; those incomplete outputs must not be compared as successful equivalents.

`img2pdf` outputstream avoids building a second full PDF bytes object but retains compressed image objects. Source review and measured RSS therefore do not support constant-memory claims. Current budgeting bounds image inputs and worker concurrency, not native allocator behavior. One worker remains the default; extra threads should be selected from the workload's measurements. Process scheduling was not benchmarked and is not implemented. Hard memory/time isolation would be a separate feature.

## Private real-page validation

`benchmarks/real_world.py` can repack image-only PDFs into CBZ fixtures, then run repeated new-converter trials:

```sh
python benchmarks/real_world.py /path/to/volume1.pdf /path/to/volume2.pdf --trials 3 --work benchmarks/work/private-run --output benchmarks/reports/private-run.json
```

The fixture writer preserves existing JPEG streams exactly; other embedded images export to lossless PNG. This tests actual page content, not the original archive structure or source PDF layout/text. Source PDFs are hashed before/after preparation. Generated CBZs and PDFs remain in the ignored work directory. Reports use anonymous volume labels and contain metrics/hashes, not manga page content. No private image fixtures are committed. Compressed CBR performance is not measured because no representative compressed comic RAR fixture is available.

## Recorded run and interpretation

The primary comparison contains 72 trials: eight workloads × three implementations × three trials, one archive worker each. `scaling-exploration.json` contains 168 earlier thread-scaling trials; its metadata explains shared-host overlap and the verification enhancement during that exploration. Use the primary comparison for final sequential conclusions. The source digest in each report identifies the measured code; a subsequent cleanup-only failure-path fix is identified separately, with final-code smoke evidence.

Measured environment: AMD Ryzen 7 3800X (8 cores / 16 logical CPUs), approximately 31.3 GiB RAM, Linux x86-64, CPython 3.14.9. Runtime dependencies were obtained as inspected upstream source because direct package downloads were blocked. In particular, pikepdf was absent, so the historical fork selected img2pdf's internal engine; ordinary pip installations may select pikepdf instead. These results should not be extrapolated to that unmeasured configuration.

The redesign preserved every synthetic page and matched decoded pixels in expected order in all primary trials. It was faster than original CB2pdf on the tested JPEG/scan workloads, but slower than the fork for some directly embeddable JPEG and PNG workloads. Hash verification and fsync are included in redesign timing. Memory is workload-dependent: preserving large JPEG streams can use more RSS than historical lossy encoding.

Private real-content validation covers 98, 184 and 183 pages, three trials each: all 465 pages per trial matched exported fixture pixels in order. The third source PDF required recovery for missing ASCIIHex end markers; warning counts are retained. Its indexed palette is exported explicitly, with a regression test and an independent Poppler pixel check on one page. All three source PDF hashes remained unchanged. This validates exported page content, not original comic-archive structure or every source PDF's rendering.
