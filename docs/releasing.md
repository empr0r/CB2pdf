# Release validation

CB2pdf 2.0.0 passed all eighteen jobs in
[CI run 41763768811](https://github.com/empr0r/CB2pdf/actions/runs/41763768811):
sixteen installed-wheel configurations, package build/strict metadata checks and
quality checks. The tested commit is `22b2beb1d2a23304f8ec0593dc67049ecbb00a6d`.
See the [final engineering report](../validation/release-2.0.0/FINAL-REPORT.md)
and [artifact receipt](../validation/release-2.0.0/final-report.json) for exact
build identities, results and limitations. These records describe those tested
artifacts; later documentation edits do not replace them with a new build.

## Platform gate

| Platform | Installed-wheel configurations |
|---|---|
| Linux | Python 3.11–3.14/latest dependencies, 3.11/minimum, 3.14/basic without extras |
| Windows | Python 3.11–3.14/latest dependencies, 3.11/minimum |
| macOS | Python 3.11–3.14/latest dependencies, 3.11/minimum |

The final run executed 1,855 passing tests with 49 expected optional
backend/renderer skips and zero failures/errors. Each configuration discovered
119 test slots. Every job also passed installed-version and six-page exact-pixel/
JPEG-stream smoke checks. Six additional local Linux environments passed 695
executed tests with 19 expected skips. Individual reports retain exact dependency,
interpreter, OS and native-decoder identities.

The tested dependency floor on Python 3.11 is Pillow 10.4.0, img2pdf 0.6.3,
pypdf 6.12.0 and optional rarfile 4.2. Latest resolved versions at qualification
were Pillow 13.0.0, img2pdf 0.6.3, pypdf 6.21.4, pikepdf 10.17.0 and rarfile 4.5.
Pikepdf is transitive; CB2pdf explicitly selects img2pdf's internal writer.

## Reproduce an installed-artifact run

Build through ordinary isolated packaging. Use a fresh output directory to
avoid mixing artifacts from different builds:

```sh
python -m pip install build twine
python -m build --outdir dist/new-validation
python -m twine check --strict dist/new-validation/*
```

In a fresh virtual environment of the desired Python version:

```sh
python -m pip install './dist/new-validation/cb2pdf-2.0.0-py3-none-any.whl[rar,dev,benchmark]'
# Optional: reproduce the runtime floor on Python 3.11
python -m pip install Pillow==10.4.0 img2pdf==0.6.3 pypdf==6.12.0 rarfile==4.2
python -m pip check
python tools/validate_release.py --artifact dist/new-validation/cb2pdf-2.0.0-py3-none-any.whl --report validation/new-run.json --require-rar
```

Install compatible native decoders separately and put them on PATH. The runner
never installs tools, downloads data or publishes anything. Reports and adjacent
logs require unused paths. Fixtures/tools are included in source distributions,
so validation also works from an extracted source archive.

The runner stages tests and small synthetic fixtures outside the checkout,
removes PYTHONPATH/PYTHONHOME overrides, and verifies the package lives inside
the selected environment. Every installed package file is compared with the
wheel, and module/distribution versions must agree. This prevents an editable
checkout or compatibility launcher from masking packaging defects. CLI checks
run through that installed interpreter. JSON records retain failures, explicit
skips, dependency versions, artifact SHA-256 and native backend identities.

## Native RAR coverage

Five tiny synthetic fixtures in `tests/fixtures/rar` cover compressed ordinary
and solid RAR4/RAR5. Tests independently extract native bytes, compare output
pixels/order and exercise corruption, limits and literal member selectors.
No archiver binary or private manga content is distributed.

The scoped rarfile adapter repairs bsdtar argument order without modifying
global library behavior. Bsdtar supports ordinary RAR4 and ordinary/solid RAR5;
solid RAR4 produces an actionable dependency error. 7-Zip capability detection
checks enabled decoder methods rather than advertised archive formats. Missing
methods must produce explicit failures; native crashes remain test failures.

Linux CI uses official 7-Zip 26.05, downloaded into a job-owned directory and
verified before execution against archive SHA-256
`22cf82fcc6eb7474f1d5bb4f02c0f8ebd573a718089d6833dc30f8350a3b232e`.
The selected executable version and digest are recorded. The Ubuntu
23.01+dfsg-11 / RAR-plugin 23.01-4 pair crashed on valid RAR4 fixtures; the
[retained reproduction](../validation/ci-environment-correction/README.md)
explains that environment correction. macOS unar provides working conversion;
stripped Homebrew 7-Zip codecs are tested as explicit missing capabilities.

## Workflow and evidence policy

[The CI workflow](../.github/workflows/ci.yml) builds one wheel/source archive,
checks metadata and shares the same wheel with all sixteen test configurations.
RAR-enabled jobs require a backend; the basic job omits extras. Jobs upload the
current JSON report and full log even after failure. A separate quality job
runs typing, lint and formatting checks. Workflow structure is checked locally
with actionlint.

CI runs on push, pull request and manual dispatch with read-only repository
permissions. It does not tag, publish, merge or create releases automatically.
Retain receipts for the exact reviewed artifacts; superseded candidate runs are
indexed in [validation history](../validation/README.md). Audit records remain
outside package build inputs. Package README/docs edits still change distribution
contents and require a fresh build before publication.

## Release checklist

1. Review all sixteen installed-wheel cases, native decoder coverage/skips,
   Windows filesystem behavior and package/quality jobs. Resolve failures.
2. Verify versions/changelog, fresh installation, fixture provenance, source
   archive contents and artifact SHA-256 identities.
3. Confirm required pages, preservation checks and source-safety tests pass.
   Broader color-managed/high-depth/large-document validation remains valuable.
4. Retain results for the exact stable artifacts. A qualified candidate or older
   wheel does not validate a substituted rebuild.
5. Obtain explicit authorization before publishing packages, pushing release
   tags or creating remote releases. Use the reviewed artifact bytes.

Hard native memory/time isolation and standalone executables remain future work.
Unsupported archive/sample variants must remain explicit failures.
