# Development measurement — superseded

This run predates the final implementation. Use [verified measurements](performance-verified.md) and [the performance report](performance-summary.md) for final claims.

Fixed-seed fixtures, randomized variant order, fresh process per trial. One archive at a time; bounded hash helper thread permitted. Baseline/current verification, SHA-256 and fsync remain enabled. Every page receives decoded pixel and completeness validation outside conversion timing. Fork defaults can resize/recompress/omit formats; fidelity columns distinguish these cases. Shared host, warm filesystem caches, no pikepdf installed.

| Workload | Variant | Median seconds | Peak RSS MiB | Exact ordered pixels | Pages |
|---|---|---:|---:|---:|---:|
| small-jpeg | baseline | 0.0531 | 59.7 | 12/12 | 12/12 |
| small-jpeg | fork | 0.0548 | 65.1 | 12/12 | 12/12 |
| small-jpeg | optimized | 0.0520 | 59.7 | 12/12 | 12/12 |
| large-jpeg | baseline | 0.6104 | 417.2 | 24/24 | 24/24 |
| large-jpeg | fork | 0.5249 | 485.8 | 24/24 | 24/24 |
| large-jpeg | optimized | 0.4272 | 268.4 | 24/24 | 24/24 |
| png-heavy | baseline | 0.1363 | 47.3 | 8/8 | 8/8 |
| png-heavy | fork | 0.0852 | 51.2 | 8/8 | 8/8 |
| png-heavy | optimized | 0.0168 | 42.9 | 8/8 | 8/8 |
| mixed-format | baseline | 0.1988 | 62.4 | 6/6 | 6/6 |
| mixed-format | fork | 0.1032 | 60.7 | 2/6 | 5/6 |
| mixed-format | optimized | 0.1829 | 62.1 | 6/6 | 6/6 |
| high-resolution | baseline | 0.3888 | 286.5 | 4/4 | 4/4 |
| high-resolution | fork | 1.7976 | 191.6 | 0/4 | 4/4 |
| high-resolution | optimized | 0.2476 | 224.3 | 4/4 | 4/4 |
| nested | baseline | 0.0864 | 42.7 | 12/12 | 12/12 |
| nested | fork | 0.0616 | 50.2 | 12/12 | 12/12 |
| nested | optimized | 0.0179 | 42.4 | 12/12 | 12/12 |
| many-small-volumes | baseline | 0.0892 | 56.3 | 48/48 | 48/48 |
| many-small-volumes | fork | 0.1480 | 47.6 | 48/48 | 48/48 |
| many-small-volumes | optimized | 0.0815 | 41.0 | 48/48 | 48/48 |
| several-large-volumes | baseline | 0.7483 | 395.2 | 24/24 | 24/24 |
| several-large-volumes | fork | 4.9031 | 130.2 | 0/24 | 24/24 |
| several-large-volumes | optimized | 0.5148 | 167.5 | 24/24 | 24/24 |

Exploratory run. The final implementation additionally validates opaque PNG DEFLATE streams, scanline extents and filter tags, and uses the measured 256 KiB hashing threshold. Use performance-verified.json for final-code results.
