# Local stable-artifact validation

The final version 2.0.0 wheel/source archive were rebuilt after the rc2
implementation passed all sixteen platform/dependency cases. Application
behavior is unchanged; package/module versions agree on 2.0.0.

The same local wheel passed installed-provenance, full staged-suite and CLI
smoke checks in six Linux environments: Python 3.11–3.14/latest dependencies,
Python 3.11/minimum dependencies and Python 3.14/basic installation without
extras. Of 714 discovered test slots, 695 executed tests passed and 19 expected
skips were retained. There were zero failures/errors. Exact six-page pixels and
original JPEG streams passed in every smoke run. Native decoder version and
executable identity are recorded.

`summary.json` is the local pre-platform-run record, including exact wheel/source
archive SHA-256 and runtime source identity. Local artifacts and SHA256SUMS are
under ignored `dist/2.0.0/`. The final platform run and its CI-tested artifacts
are retained separately; a successful candidate is not substituted for testing
the stable build itself. Publication is not performed automatically.

Strict Twine, mypy (18 source files), lint/style/formatting, compilation,
Python 3.11 grammar, actionlint, dependency checks and distribution content
inspection passed. The wheel package bytes match current source; source archives
exclude private work and validation audit records. The latter are separate
evidence, not package build inputs. Adjacent full logs remain local and ignored.
