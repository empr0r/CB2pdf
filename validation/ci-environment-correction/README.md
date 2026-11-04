# Linux native decoder correction

`native-reproduction.json` records eight real native extraction attempts on the
same synthetic fixtures. The checksum-verified Ubuntu package/plugin pair
crashes on RAR4 and succeeds on RAR5. The official 7-Zip 26.05 archive decodes
all four fixtures to the expected member SHA-256. Core dumps were disabled for
this controlled reproduction. Downloaded executables/packages remain ignored
local tooling; none is redistributed.

`local-installed.json` records the installed rc2 wheel tested outside the
checkout on Python 3.11 with minimum runtime dependencies and the exact official
decoder used by the corrected CI configuration. Of 119 tests, 118 passed and
one skipped unavailable unar. CLI/smoke, original bytes/pixels, wheel provenance,
RAR limits and source preservation checks passed. Native decoder version and
executable identity are retained. Actionlint, Python lint/style and formatting
checks passed for the changed workflow/release runner.

The update changes CI provisioning and diagnostic metadata. Application source
digest remains `d1ddbda462662b227333af980a632b9dc648eac8c6c550c1d5770ab5d12fc7be`.
It does not turn crashes into acceptable test outcomes. A native codec listing
alone cannot prove implementation correctness; the real extraction assertions
remain the release gate.
