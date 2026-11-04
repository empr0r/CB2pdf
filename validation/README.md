# Validation evidence

The current release record is [CB2pdf 2.0.0](release-2.0.0/FINAL-REPORT.md).
Its [machine-readable receipt](release-2.0.0/final-report.json) identifies the
tested commit, artifact hashes and final CI run. The directory retains all
sixteen platform reports and six additional local installed-wheel reports.
Earlier snapshots inside that release directory are labeled as historical;
the final receipt is the readiness verdict.

The [native decoder reproduction](ci-environment-correction/README.md) retains
the evidence distinguishing a crashing Ubuntu 7-Zip/plugin pair from a working
upstream decoder. This is still useful for diagnosing backend failures.

## Retired records

Superseded candidate runs and intermediate reports have been removed from the
working tree. Their original contents remain accessible at these immutable
Git revisions:

| Record | Archived copy |
|---|---|
| First candidate's failed platform run | [CI 41745898306](https://github.com/empr0r/CB2pdf/tree/362900da51e1019c968c9e3bd1677e9c4c853837/validation/ci-run-41745898306) |
| Second run and Linux native crash | [CI 41760345855](https://github.com/empr0r/CB2pdf/tree/362900da51e1019c968c9e3bd1677e9c4c853837/validation/ci-run-41760345855) |
| Qualified second candidate | [CI 41761823987](https://github.com/empr0r/CB2pdf/tree/362900da51e1019c968c9e3bd1677e9c4c853837/validation/ci-run-41761823987) |
| Local candidate validation | [rc1](https://github.com/empr0r/CB2pdf/tree/362900da51e1019c968c9e3bd1677e9c4c853837/validation/release-2.0.0rc1), [rc2](https://github.com/empr0r/CB2pdf/tree/362900da51e1019c968c9e3bd1677e9c4c853837/validation/release-2.0.0rc2) |
| Initial project assessment | [Assessment](https://github.com/empr0r/CB2pdf/blob/362900da51e1019c968c9e3bd1677e9c4c853837/docs/assessment.md) |
| Initial implementation delivery | [Engineering report](https://github.com/empr0r/CB2pdf/blob/362900da51e1019c968c9e3bd1677e9c4c853837/docs/engineering-report.md) |

For new validation runs, follow [the maintainer guide](../docs/releasing.md).
Keep reports supporting the current release; full local logs, environments and
build outputs remain ignored. Audit records are excluded from distributions.
