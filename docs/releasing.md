# Release validation: 2.0.0rc1

This candidate is prepared locally and has not been published. A stable release
remains gated on successful Windows/macOS runs and review of the CI results.
The feature set is frozen; the release pass changes conversion behavior only
where real regression fixtures demonstrated a defect.

## Local evidence

The same installed wheel is tested outside the checkout in six environments:

| Linux interpreter | Runtime dependencies | Suite |
|---|---|---|
| CPython 3.11.18 | Latest compatible | 116 tests |
| CPython 3.12.16 | Latest compatible | 116 tests |
| CPython 3.13.18 | Latest compatible | 116 tests |
| CPython 3.14.9 | Latest compatible | 116 tests |
| CPython 3.11.18 | Declared runtime floor | 116 tests |
| CPython 3.14.9 | Basic runtime only (no extras) | 116 tests; RAR tests skipped |

Latest resolved versions: Pillow 13.0.0, img2pdf 0.6.3, pypdf 6.21.4,
pikepdf 10.17.0 and rarfile 4.5. The explicit floor is Pillow 10.4.0,
img2pdf 0.6.3, pypdf 6.12.0 and rarfile 4.2. Pikepdf is a transitive dependency;
CB2pdf continues to select img2pdf's internal writer.

Packages and build dependencies were downloaded through normal index resolution
into isolated environments. Each run checks that every installed package file
matches the supplied wheel, that module/distribution versions agree, and that
the package resides inside that environment. It stages tests and small synthetic
fixtures outside the checkout, removing PYTHONPATH/PYTHONHOME overrides. This
prevents the compatibility launcher or an editable checkout masking an installed
artifact defect. CLI/version and six-page exact-pixel/JPEG-stream smoke checks
run through the installed interpreter too.

Individual JSON records retain test failures, explicit decoder skips, dependency
versions, platform, wheel SHA-256 and smoke results. Full adjacent logs are kept
locally. Unar is unavailable on the local host, so its one dedicated test is
explicitly skipped in the five RAR-enabled runs. The basic-install run omits the
optional rarfile library and records those expected RAR skips separately. UnRAR, 7-Zip and bsdtar tests run locally; unavailable tools
are not described as verified.

## Compressed RAR findings

`tests/fixtures/rar` contains five tiny synthetic archives, generated separately
using RAR 6.24. No archiver binary or private manga content is distributed.
Both ordinary and solid RAR4/RAR5 are exercised with actual compression, exact
decoded pixels/order, checksums, corruption and resource-limit failures.

Real tests found rarfile 4.2 and 4.5 constructs bsdtar arguments as `-f -- ARCHIVE`.
Bsdtar treats `--` as the filename. `rar_backend.py` repairs the argument order
for that backend only, retaining rarfile's seekable CRC-checking PipeReader.
It never patches process-global library behavior or extracts archive names.
Literal member selectors escape bsdtar's glob syntax; bracket names are tested
against a nearby nonliteral match.

UnRAR 6.24 and 7-Zip 26.05 pass ordinary/solid RAR4/RAR5. Bsdtar 3.8.11 passes
ordinary RAR4 and ordinary/solid RAR5. It explicitly lacks solid RAR4 support;
CB2pdf reports MissingDependencyError with alternative decoders before producing
output. This is a backend limitation, not a corrupt-archive diagnosis.

## Reproduce an installed-artifact run

Build with ordinary isolated packaging:

```sh
python -m pip install build twine
python -m build --outdir dist/2.0.0rc1
python -m twine check --strict dist/2.0.0rc1/*
```

In a fresh virtual environment of the desired Python version:

```sh
python -m pip install './dist/2.0.0rc1/cb2pdf-2.0.0rc1-py3-none-any.whl[rar,dev,benchmark]'
# Optional: reproduce the supported runtime floor, on Python 3.11
python -m pip install Pillow==10.4.0 img2pdf==0.6.3 pypdf==6.12.0 rarfile==4.2
python -m pip check
python tools/validate_release.py --artifact dist/2.0.0rc1/cb2pdf-2.0.0rc1-py3-none-any.whl --report validation/new-run.json --require-rar
```

Install a compatible decoder separately and put it on PATH. The validation
command never installs tools, downloads data or publishes anything. Reports and
logs require unused paths; previous results are protected. The same commands
work from an extracted source distribution because fixtures/tools are included.

## Automated platform gate

`.github/workflows/ci.yml` builds one wheel/source distribution, validates their
metadata and shares those artifacts with all test jobs. Twelve latest-dependency
OS/Python combinations, three Python 3.11 dependency-floor combinations and one
Linux basic-install configuration test the installed wheel. The basic job omits
extras to catch undeclared runtime dependencies. Native decoders are installed per platform; RAR backend
availability is required in RAR-enabled jobs. Every job uploads its JSON and logs even on failures.
A separate quality job checks typing, lint and formatting. Actionlint validates
workflow structure locally, but cannot establish remote execution success.

The workflow runs on push, pull request or manual dispatch. No publishing,
release creation or elevated repository write permissions are configured.
Remote execution requires the reviewed branch to exist on GitHub. The original
authorization requires explicit approval before a push; that boundary remains.

## Stable-release checklist

1. Review all sixteen installed-wheel CI configurations, including native RAR
   coverage/skips and Windows filesystem behavior. Fix failures before release.
2. Review fresh-install and metadata checks, fixture provenance, build contents
   and artifact SHA-256 identities. Retain evidence for the exact candidate.
3. Resolve any release-blocking preservation or source-safety regressions.
   Broader color-managed/high-depth/large-document testing remains valuable;
   documented unsupported cases must remain explicit failures.
4. After validation, align the package/module stable version and changelog,
   rebuild and revalidate the actual stable artifacts. A tested candidate does
   not authorize silently substituting different stable artifacts.
5. Publishing, tags pushed to remotes and remote release creation require
   explicit authorization. None is performed by this workflow or local tooling.

Hard native memory/time isolation, standalone executables and untested backend
variants remain documented limitations rather than claims made by this release.
