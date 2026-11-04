# Measured comparison

This initial comparison predates the performance optimization. For the later
five-trial measurements, see [the performance summary](performance-summary.md).

Fixed-seed textured images. Fresh process per trial. Original batch sleep=0; fork sequential; default quality policies differ. Conversion includes redesign verification/fsync. Fidelity is checked outside timing for every page. Temporary logical byte samples every 5 ms are lower bounds. CBR not measured: no representative comic RAR fixture.

| Workload | Implementation | Workers | Median seconds | Peak RSS MiB | Output MiB | Exact ordered pixels | Pages |
|---|---|---:|---:|---:|---:|---:|---:|
| high-resolution | fork | 1 | 1.8424 | 191.7 | 11.53 | 0/4 | 4/4 |
| high-resolution | original | 1 | 1.2748 | 299.4 | 30.89 | 0/4 | 4/4 |
| high-resolution | redesigned | 1 | 0.3834 | 286.9 | 124.48 | 4/4 | 4/4 |
| large-jpeg | fork | 1 | 0.4962 | 486.3 | 212.72 | 24/24 | 24/24 |
| large-jpeg | original | 1 | 2.1699 | 408.7 | 52.88 | 0/24 | 24/24 |
| large-jpeg | redesigned | 1 | 0.5872 | 391.0 | 212.72 | 24/24 | 24/24 |
| many-small-volumes | fork | 1 | 0.1421 | 46.3 | 17.06 | 48/48 | 48/48 |
| many-small-volumes | original | 1 | 0.2265 | 45.6 | 4.28 | 0/48 | 48/48 |
| many-small-volumes | redesigned | 1 | 0.0870 | 56.5 | 17.06 | 48/48 | 48/48 |
| mixed-format | fork | 1 | 0.1114 | 61.1 | 4.85 | 2/6 | 5/6 |
| mixed-format | original | 1 | 0.0634 | 53.1 | 1.10 | 0/6 | 2/6 |
| mixed-format | redesigned | 1 | 0.2108 | 62.9 | 3.96 | 6/6 | 6/6 |
| nested | fork | 1 | 0.0581 | 48.7 | 2.14 | 12/12 | 12/12 |
| nested | original | 1 | 0.1055 | 68.7 | 3.75 | 0/12 | 12/12 |
| nested | redesigned | 1 | 0.0929 | 43.2 | 2.14 | 12/12 | 12/12 |
| png-heavy | fork | 1 | 0.0932 | 64.9 | 2.52 | 8/8 | 8/8 |
| png-heavy | original | 1 | 0.1676 | 95.8 | 7.21 | 0/8 | 8/8 |
| png-heavy | redesigned | 1 | 0.1463 | 47.7 | 2.52 | 8/8 | 8/8 |
| several-large-volumes | fork | 1 | 4.6107 | 145.6 | 89.21 | 0/24 | 24/24 |
| several-large-volumes | original | 1 | 2.6254 | 203.2 | 64.51 | 0/24 | 24/24 |
| several-large-volumes | redesigned | 1 | 0.7758 | 393.5 | 259.01 | 24/24 | 24/24 |
| small-jpeg | fork | 1 | 0.0561 | 65.2 | 10.90 | 12/12 | 12/12 |
| small-jpeg | original | 1 | 0.1459 | 61.7 | 2.72 | 0/12 | 12/12 |
| small-jpeg | redesigned | 1 | 0.0467 | 59.8 | 10.90 | 12/12 | 12/12 |

The measured source predates a cleanup-only change that attempts temporary unlink even if buffered close fails. Successful conversion logic is unchanged; the [archived final smoke record](https://github.com/empr0r/CB2pdf/blob/362900da51e1019c968c9e3bd1677e9c4c853837/benchmarks/reports/final-smoke.json) and that revision's test suite validated the change. Dependency source loading and the absence of pikepdf are recorded in the JSON environment metadata.
