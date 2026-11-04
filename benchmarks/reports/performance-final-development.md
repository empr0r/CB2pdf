# Development measurement — superseded

This run predates the final implementation. Use [verified measurements](performance-verified.md) and [the performance report](performance-summary.md) for final claims.

Fixed-seed fixtures, randomized variant order, fresh process per trial. One archive at a time; bounded hash helper thread permitted. Baseline/current verification, SHA-256 and fsync remain enabled. Every page receives decoded pixel and completeness validation outside conversion timing. Fork defaults can resize/recompress/omit formats; fidelity columns distinguish these cases. Shared host, warm filesystem caches, no pikepdf installed.

| Workload | Variant | Median seconds | Peak RSS MiB | Exact ordered pixels | Pages |
|---|---|---:|---:|---:|---:|
| small-jpeg | baseline | 0.0527 | 59.5 | 12/12 | 12/12 |
| small-jpeg | fork | 0.0542 | 65.4 | 12/12 | 12/12 |
| small-jpeg | optimized | 0.0414 | 59.7 | 12/12 | 12/12 |
| large-jpeg | baseline | 0.6119 | 417.2 | 24/24 | 24/24 |
| large-jpeg | fork | 0.5154 | 485.9 | 24/24 | 24/24 |
| large-jpeg | optimized | 0.4310 | 268.6 | 24/24 | 24/24 |
| png-heavy | baseline | 0.1436 | 47.1 | 8/8 | 8/8 |
| png-heavy | fork | 0.0832 | 51.2 | 8/8 | 8/8 |
| png-heavy | optimized | 0.0684 | 44.7 | 8/8 | 8/8 |
| mixed-format | baseline | 0.2059 | 62.4 | 6/6 | 6/6 |
| mixed-format | fork | 0.1094 | 60.5 | 2/6 | 5/6 |
| mixed-format | optimized | 0.2022 | 62.0 | 6/6 | 6/6 |
| high-resolution | baseline | 0.3965 | 286.6 | 4/4 | 4/4 |
| high-resolution | fork | 1.8325 | 191.8 | 0/4 | 4/4 |
| high-resolution | optimized | 0.2606 | 224.6 | 4/4 | 4/4 |
| nested | baseline | 0.0925 | 42.6 | 12/12 | 12/12 |
| nested | fork | 0.0568 | 50.1 | 12/12 | 12/12 |
| nested | optimized | 0.0439 | 42.3 | 12/12 | 12/12 |
| many-small-volumes | baseline | 0.0818 | 56.3 | 48/48 | 48/48 |
| many-small-volumes | fork | 0.1483 | 47.5 | 48/48 | 48/48 |
| many-small-volumes | optimized | 0.0737 | 41.3 | 48/48 | 48/48 |
| several-large-volumes | baseline | 0.7688 | 395.0 | 24/24 | 24/24 |
| several-large-volumes | fork | 4.8114 | 129.8 | 0/24 | 24/24 |
| several-large-volumes | optimized | 0.5096 | 167.7 | 24/24 | 24/24 |
