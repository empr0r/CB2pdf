# Rc2 platform run

[Run 41760345855](https://github.com/empr0r/CB2pdf/actions/runs/41760345855)
tested `b3868d75756ce4a6913792cc740378dbd27d3f28` (2.0.0rc2).
All sixteen per-job report archives were verified against GitHub's artifact
SHA-256 before retaining their JSON. Raw results are unchanged.

Build/quality, all five Windows configurations, all five macOS configurations
and Linux basic installation passed. Five Linux RAR-enabled configurations
failed. Their only failures were the independent native RAR4 extraction
assertions: 7-Zip returned -11 (SIGSEGV) while advertising a Rar3 decoder.
No native crash is accepted as a successful or missing-codec outcome.

This distinguishes the Linux failure from Homebrew's genuinely absent codecs,
which rc2 now identifies correctly. An isolated Ubuntu 7zip 23.01+dfsg-11 plus
7zip-rar 23.01-4 reproduces the native crash on both valid RAR4 fixtures.
Official 7-Zip 26.05 preserves the exact native bytes for ordinary/solid
RAR4/RAR5. The CI environment correction pins that verified upstream binary;
the application source and strict extraction/pixel assertions are unchanged.

See [local native evidence](../ci-environment-correction/README.md). This run
remains a failed release gate; a subsequent corrected-environment run is needed.
