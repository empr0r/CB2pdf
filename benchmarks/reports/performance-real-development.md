# Development measurement — superseded

This run predates the final implementation. Use [verified measurements](performance-verified.md) and [the performance report](performance-summary.md) for final claims.

Fixed-seed fixtures, randomized variant order, fresh process per trial. One archive at a time; bounded hash helper thread permitted. Baseline/current verification, SHA-256 and fsync remain enabled. Every page receives decoded pixel and completeness validation outside conversion timing. Fork defaults can resize/recompress/omit formats; fidelity columns distinguish these cases. Shared host, warm filesystem caches, no pikepdf installed.

| Workload | Variant | Median seconds | Peak RSS MiB | Exact ordered pixels | Pages |
|---|---|---:|---:|---:|---:|
| fixture-1 | baseline | 0.3202 | 217.3 | 98/98 | 98/98 |
| fixture-1 | fork | 0.2730 | 222.9 | 98/98 | 98/98 |
| fixture-1 | optimized | 0.2581 | 131.0 | 98/98 | 98/98 |
| fixture-2 | baseline | 0.2845 | 156.0 | 184/184 | 184/184 |
| fixture-2 | fork | 0.2106 | 159.8 | 184/184 | 184/184 |
| fixture-2 | optimized | 0.2099 | 98.9 | 184/184 | 184/184 |
| fixture-3 | baseline | 2.3420 | 190.7 | 183/183 | 183/183 |
| fixture-3 | fork | 1.5458 | 145.8 | 3/183 | 183/183 |
| fixture-3 | optimized | 1.4705 | 122.9 | 183/183 | 183/183 |
