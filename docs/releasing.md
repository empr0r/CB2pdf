# Release validation: 2.0.0

The rc2 implementation passed all sixteen platform/dependency configurations
and the build/quality jobs in
[run 41761823987](https://github.com/empr0r/CB2pdf/actions/runs/41761823987).
Version 2.0.0 promotes that implementation without changing conversion behavior.
The stable version receives its own artifact build and validation; no package
release, remote tag or merge to the default branch is performed automatically.
Publication requires explicit authorization.

## Local evidence

The same installed wheel is tested outside the checkout in six environments:

| Linux interpreter | Runtime dependencies | Suite |
|---|---|---|
| CPython 3.11.18 | Latest compatible | 119 tests |
| CPython 3.12.16 | Latest compatible | 119 tests |
| CPython 3.13.18 | Latest compatible | 119 tests |
| CPython 3.14.9 | Latest compatible | 119 tests |
| CPython 3.11.18 | Declared runtime floor | 119 tests |
| CPython 3.14.9 | Basic runtime only (no extras) | 119 tests; RAR tests skipped |

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
python -m build --outdir dist/2.0.0
python -m twine check --strict dist/2.0.0/*
```

In a fresh virtual environment of the desired Python version:

```sh
python -m pip install './dist/2.0.0/cb2pdf-2.0.0-py3-none-any.whl[rar,dev,benchmark]'
# Optional: reproduce the supported runtime floor, on Python 3.11
python -m pip install Pillow==10.4.0 img2pdf==0.6.3 pypdf==6.12.0 rarfile==4.2
python -m pip check
python tools/validate_release.py --artifact dist/2.0.0/cb2pdf-2.0.0-py3-none-any.whl --report validation/new-run.json --require-rar
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

## First remote CI run and rc2 correction

[Run 41745898306](https://github.com/empr0r/CB2pdf/actions/runs/41745898306)
validated rc1. Build/metadata and quality jobs passed, all five Windows cases
passed, and the Linux basic-install case passed. The remaining ten jobs failed
only in dedicated 7-Zip tests: distribution 7-Zip variants could not decode the selected RAR fixtures.
Subsequent diagnostics separated missing macOS codecs from a Linux native crash. Their other conversion, preservation and filesystem tests passed.
This is a failed release gate, not a claim that all platforms are green.

Candidate rc2 checks enabled methods in `7z i`'s Codecs section rather than
assuming an installed executable or advertised RAR format can decode it. It
checks compressed members' required Rar1/Rar2/Rar3/Rar5 method, uses a finite
query timeout, and reports MissingDependencyError with installation guidance
when a decoder is absent. Stored members need no compression codec.

The backend tests independently invoke the native decoder against valid
fixtures. Available codecs must produce the original bytes and exact PDF pixels;
missing codecs must both fail native extraction with Unsupported Method and
produce the application's explicit source-preserving dependency error. Pure
parser tests ensure an archive format or encoder flag cannot masquerade as a
decoder. CI records the codec profile, prints failure diagnostics in its console,
and uploads only the current job's report/log.

The Ubuntu package was independently downloaded into ignored test tooling,
verified against its published SHA-256 and exercised without system installation.
It reproduces a stripped-codec build. Full Arch 7-Zip continues to pass conversion
for all four compressed/solid fixtures. No decoder failure is silently skipped.

Distribution details: [Ubuntu 7zip/optional RAR plugin](https://packages.ubuntu.com/noble/7zip),
[Homebrew build configuration](https://github.com/Homebrew/homebrew-core/blob/HEAD/Formula/s/sevenzip.rb).

## rc2 platform results and Linux decoder correction

[Run 41760345855](https://github.com/empr0r/CB2pdf/actions/runs/41760345855)
passed build/quality, all five Windows cases, all five macOS cases and Linux's
basic install. Five Linux RAR-enabled jobs failed because their native 7-Zip
process terminated with SIGSEGV (-11) on the valid RAR4 fixtures. The tests
correctly rejected the crash despite the advertised Rar3 decoder. The earlier
missing-codec explanation did not fully explain the Linux failure.

An isolated reproduction with Ubuntu 7zip 23.01+dfsg-11 and its 23.01-4 RAR
plugin produces the same crash on both RAR4 fixtures, while RAR5 succeeds.
Official 7-Zip 26.05 decodes all four fixtures to their original bytes. CI now
uses that exact upstream Linux binary in a job-owned temporary directory,
verified against SHA-256
`22cf82fcc6eb7474f1d5bb4f02c0f8ebd573a718089d6833dc30f8350a3b232e`
before execution. No decoder binary is added to the repository or application
distributions. The application runtime source and strict native extraction
assertions are unchanged by this environment correction.

Release reports also retain the selected 7-Zip version header, executable path
and executable SHA-256 alongside its codec list. Codec availability establishes
which methods are present; it cannot guarantee a native implementation is free
of bugs. A crash remains a failed test. See
[upstream release](https://github.com/ip7z/7zip/releases/tag/26.05) and the
[retained second-run records](../validation/ci-run-41760345855/README.md).

## Qualified implementation

The corrected-environment rc2 run completed all eighteen jobs successfully:
16 installed-wheel cases, build/strict metadata checks and quality checks.
All job report archives are retained with SHA-256 verification under
[validation/ci-run-41761823987](../validation/ci-run-41761823987/summary.json).
The raw reports preserve expected backend/renderer skips rather than hiding
them. The same CI-built wheel was tested in every platform case.

A successful candidate qualifies the implementation; the stable-version wheel
and source distribution are rebuilt and checked with their own identities.
The final stable artifact records are retained separately under
`validation/release-2.0.0` and its corresponding platform run.
