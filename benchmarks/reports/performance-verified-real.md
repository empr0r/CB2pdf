# Performance comparison

Fixed-seed fixtures, randomized variant order, fresh process per trial. One archive at a time; bounded hash helper thread permitted. Baseline/current verification, SHA-256 and fsync remain enabled. Every page receives decoded pixel and completeness validation outside conversion timing. Fork defaults can resize/recompress/omit formats; fidelity columns distinguish these cases. Shared host, warm filesystem caches, no pikepdf installed.

| Workload | Variant | Median seconds | Peak RSS MiB | Exact ordered pixels | Pages |
|---|---|---:|---:|---:|---:|
| fixture-1 | baseline | 0.3589 | 217.5 | 98/98 | 98/98 |
| fixture-1 | fork | 0.2790 | 223.0 | 98/98 | 98/98 |
| fixture-1 | optimized | 0.2510 | 131.3 | 98/98 | 98/98 |
| fixture-2 | baseline | 0.2722 | 155.9 | 184/184 | 184/184 |
| fixture-2 | fork | 0.2063 | 159.7 | 184/184 | 184/184 |
| fixture-2 | optimized | 0.2127 | 99.0 | 184/184 | 184/184 |
| fixture-3 | baseline | 2.2891 | 191.0 | 183/183 | 183/183 |
| fixture-3 | fork | 1.5402 | 146.7 | 3/183 | 183/183 |
| fixture-3 | optimized | 1.4326 | 122.5 | 183/183 | 183/183 |
