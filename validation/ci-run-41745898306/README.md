# First remote release-validation run

[GitHub Actions run 41745898306](https://github.com/empr0r/CB2pdf/actions/runs/41745898306)
tested commit `7973060a0d85358075767f43c7490dc6c255f677` (2.0.0rc1).
The overall run failed. Raw per-job JSON was downloaded through the GitHub
connector; each archive was verified against GitHub's artifact SHA-256 before
reading its current-job `result.json`.

- Build, strict package metadata checks and the quality job passed.
- All five Windows configurations passed (3.11–3.14/latest and 3.11/minimum).
- Linux's basic-install configuration passed.
- Five Linux RAR-enabled cases failed only in 7-Zip's RAR4 fixture subtests.
- Five macOS cases failed only in 7-Zip's RAR4/RAR5 fixture subtests.

There were no other test failures/errors in these reports. The native backends
chosen by default (Linux UnRAR and macOS unar) passed the compressed/solid
round trips. Installed 7-Zip distribution builds lacked the necessary decoders,
which the original optional-backend tests had incorrectly assumed were present.
Stored-RAR, other image/PDF, ordering, source-safety and CLI tests passed.
Windows skips for unavailable Unix decoders/Poppler remain explicit in JSON.

Candidate rc2 adds enabled-codec inspection and tests the missing-codec outcome
against independent native extraction; supported methods still require exact
pixels. This directory preserves the failed gate rather than rewriting its
results as success. A new run on the corrected candidate is still required.
