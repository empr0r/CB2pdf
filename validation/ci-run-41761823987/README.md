# Qualified rc2 implementation

[Run 41761823987](https://github.com/empr0r/CB2pdf/actions/runs/41761823987)
tested `432acec6291c324be223f1db23d69d25e07a64d9` (2.0.0rc2).
All eighteen jobs passed: sixteen installed-wheel configurations, package build
and strict metadata checks, and the quality job.

All sixteen report archives were verified against GitHub's artifact SHA-256
before retaining the raw JSON. The same CI-built wheel passed every case.
The suite discovered 119 tests per job: **1,855 executed tests passed**,
49 expected decoder/renderer skips, zero failures/errors. Platform and dependency
versions, exact wheel/source identities, explicit skips and native decoder
profiles remain in each report. Six-page exact pixel/JPEG smoke checks passed.

Linux uses the checksum-pinned official 7-Zip 26.05 binary. macOS exercises
the working unar backend and explicit missing-codec outcomes for Homebrew's
7-Zip build. Windows exercises its full 7-Zip decoder; unavailable Unix decoders
and Poppler remain visible skips. No native crash or corrupt output is accepted
as a successful conversion.

The implementation is qualified; stable-version artifacts are built and
validated separately. No package index publication, remote release/tag or
default-branch merge is implied by this successful CI run.
