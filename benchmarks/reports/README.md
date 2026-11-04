# Benchmark records

Start with [the performance summary](performance-summary.md). It interprets the
final five-trial comparisons, including fidelity differences and the real-page
fixture where the fork retains a small median lead.

| Record | Purpose |
|---|---|
| [Synthetic table](performance-verified.md) / [JSON](performance-verified.json) | Final optimization comparison: eight workloads, three variants, five trials each |
| [Real-page table](performance-verified-real.md) / [JSON](performance-verified-real.json) | Final comparison on three private exported-page fixtures, five trials each |
| [Original/fork/redesign table](comparison.md) / [JSON](comparison.json) | Initial three-way comparison, before the later performance optimization |
| [Real-page preparation record](real-world.json) | Source PDF hashes, recovery diagnostics and initial exported-fixture validation |

Each JSON record identifies its source versions and environment. Historical
measurements do not establish timing for every later code/dependency version.
Raw private images and generated work fixtures are not committed.

Exploratory timing/scaling runs and superseded build smoke reports are retained
in [Git history](https://github.com/empr0r/CB2pdf/tree/362900da51e1019c968c9e3bd1677e9c4c853837/benchmarks/reports).
They predate final validation and should not be used as current performance
claims. Current installed-package evidence lives under
[release validation](../../validation/README.md).

See [methodology and reproduction](../../docs/performance.md) before comparing
results. Completeness and fidelity must be checked before ranking speed.
