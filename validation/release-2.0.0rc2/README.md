# 2.0.0rc2 local validation

This candidate corrects the decoder-capability failures identified by the
[first remote CI run](../ci-run-41745898306/README.md). It has not passed a new
remote platform run yet and is not a published stable release.

The same wheel passed installed-artifact validation outside the checkout in six
Linux environments: Python 3.11–3.14/latest dependencies, Python 3.11/minimum
runtime dependencies, and Python 3.14/basic installation without optional extras.
Each discovered 119 tests: **695 executed tests passed**, 19 expected skips,
zero failures/errors. Five RAR-enabled cases each skip unavailable unar; the
basic case skips fourteen optional RAR tests. Dependency checks passed in all
six environments. Each installed package file was byte-compared with the wheel;
CLI/version and exact six-page JPEG/pixel smoke checks passed.

The installed candidate was also exercised with the checksum-verified Ubuntu
7zip 23.01+dfsg-11 binary extracted into ignored tooling. This stripped build
reports no enabled RAR methods. All four compressed/solid RAR4/RAR5 fixtures
received MissingDependencyError, retained exact original bytes and published no
PDF (`stripped-codecs.json`). The full local 7-Zip reports Rar1/Rar2/Rar3/Rar5
and passes actual byte/pixel round trips. Three parser regressions distinguish
formats, decoders and encoder flags. Backend tests independently invoke native
extraction to validate both available and unavailable method outcomes.

`summary.json` records exact artifact/source identities. Wheel/source archive and
SHA256SUMS remain under ignored `dist/2.0.0rc2/`. Strict Twine, mypy (18 source
files), pyflakes, pycodestyle, autopep8, compilation, Python 3.11 grammar and
actionlint checks passed. Source-distribution files match the current checkout;
private working data is excluded. Full adjacent validation logs remain local.

Next gate: push this correction and review all sixteen remote configurations.
The release procedure remains [docs/releasing.md](../../docs/releasing.md).
