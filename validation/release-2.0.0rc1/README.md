# 2.0.0rc1 validation evidence

Local installed-artifact validation passed in six isolated Linux environments.
These records do not claim Windows/macOS success or stable-release readiness.

| Record | Installed configuration | Tests passed | Expected skips |
|---|---|---:|---:|
| `py311-latest.json` | Python 3.11.18, latest dependencies | 115 | 1 |
| `py312-latest.json` | Python 3.12.16, latest dependencies | 115 | 1 |
| `py313-latest.json` | Python 3.13.18, latest dependencies | 115 | 1 |
| `py314-latest.json` | Python 3.14.9, latest dependencies | 115 | 1 |
| `py311-minimum.json` | Python 3.11.18, declared runtime floor | 115 | 1 |
| `py314-basic.json` | Python 3.14.9, runtime dependencies only | 102 | 14 |

All six runs discovered 116 tests: **677 executed tests passed**, 19 expected
skips, zero failures/errors. Five skips concern unavailable `unar`; the basic
install deliberately omits rarfile and skips all fourteen RAR-specific tests.
UnRAR 6.24, 7-Zip 26.05 and bsdtar 3.8.11 run in the RAR-enabled configurations.
Known bsdtar solid-RAR4 rejection is tested as an explicit source-preserving
dependency error, not skipped or described as successful conversion.

The basic environment was installed with pip 26.3 from the final local wheel
and normal index dependencies. The other environments use normal package-index
resolution through uv. Every installed package file is compared against that
same final wheel. Tests execute from owned temporary staging directories,
without the source tree on the import path. Each run also passes an installed
CLI/version check and exact six-page self-benchmark.

`summary.json` records the wheel/source-distribution SHA-256 identities, source
digest, gate results and remaining work. Artifacts are retained locally under
`dist/2.0.0rc1/`, including `SHA256SUMS`; build products are ignored by Git.
Each run's full adjacent `.log` remains local and ignored. CI uploads its own
reports/logs as artifacts, including failures. No private manga or downloaded
archiver binaries are included in this evidence or the distributions.

Additional negative controls proved that altered wheel bytes fail provenance
checks before tests, missing required RAR support fails with retained diagnostics,
and existing reports cannot be overwritten. Strict Twine metadata validation,
typing, lint, formatting, compilation, Python 3.11 grammar and actionlint passed.
Grammar/actionlint checks do not establish remote platform execution success.

The sixteen configured installed-wheel CI cases remain pending an authorized
branch push. See [release procedure](../../docs/releasing.md) for reproduction,
decoder limitations and the stable-release gates. At the time these local records were captured, nothing had been pushed or
published. The branch was subsequently pushed; the first remote CI run is
documented in the current release procedure. Raw local records remain unchanged.
