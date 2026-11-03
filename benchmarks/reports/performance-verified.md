# Performance comparison

Fixed-seed fixtures, randomized variant order, fresh process per trial. One archive at a time; bounded hash helper thread permitted. Baseline/current verification, SHA-256 and fsync remain enabled. Every page receives decoded pixel and completeness validation outside conversion timing. Fork defaults can resize/recompress/omit formats; fidelity columns distinguish these cases. Shared host, warm filesystem caches, no pikepdf installed.

| Workload | Variant | Median seconds | Peak RSS MiB | Exact ordered pixels | Pages |
|---|---|---:|---:|---:|---:|
| small-jpeg | baseline | 0.0532 | 59.6 | 12/12 | 12/12 |
| small-jpeg | fork | 0.0540 | 65.5 | 12/12 | 12/12 |
| small-jpeg | optimized | 0.0427 | 59.9 | 12/12 | 12/12 |
| large-jpeg | baseline | 0.6006 | 417.4 | 24/24 | 24/24 |
| large-jpeg | fork | 0.5169 | 486.3 | 24/24 | 24/24 |
| large-jpeg | optimized | 0.4351 | 268.5 | 24/24 | 24/24 |
| png-heavy | baseline | 0.1453 | 47.3 | 8/8 | 8/8 |
| png-heavy | fork | 0.0875 | 51.3 | 8/8 | 8/8 |
| png-heavy | optimized | 0.0687 | 43.3 | 8/8 | 8/8 |
| mixed-format | baseline | 0.2121 | 62.5 | 6/6 | 6/6 |
| mixed-format | fork | 0.1110 | 60.7 | 2/6 | 5/6 |
| mixed-format | optimized | 0.2013 | 62.2 | 6/6 | 6/6 |
| high-resolution | baseline | 0.3900 | 286.7 | 4/4 | 4/4 |
| high-resolution | fork | 1.8654 | 191.9 | 0/4 | 4/4 |
| high-resolution | optimized | 0.2506 | 224.7 | 4/4 | 4/4 |
| nested | baseline | 0.0926 | 42.8 | 12/12 | 12/12 |
| nested | fork | 0.0626 | 50.2 | 12/12 | 12/12 |
| nested | optimized | 0.0462 | 42.2 | 12/12 | 12/12 |
| many-small-volumes | baseline | 0.0886 | 56.3 | 48/48 | 48/48 |
| many-small-volumes | fork | 0.1536 | 47.6 | 48/48 | 48/48 |
| many-small-volumes | optimized | 0.0773 | 41.6 | 48/48 | 48/48 |
| several-large-volumes | baseline | 0.7619 | 395.1 | 24/24 | 24/24 |
| several-large-volumes | fork | 4.8120 | 130.5 | 0/24 | 24/24 |
| several-large-volumes | optimized | 0.5127 | 167.6 | 24/24 | 24/24 |
