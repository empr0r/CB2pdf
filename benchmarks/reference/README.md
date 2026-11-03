# Historical benchmark references

- `original.py`: https://github.com/empr0r/CB2pdf/blob/19bc5a2cc09bfa58de98d3e0b20ab8e663dccd49/cb2pdf.py — upstream source blob `a88655d2cd238c9e2ef2b7f68e526d7cbe747f00`. MIT license in repository root, copyright 2024 empr0r.
- `fork.py`: https://github.com/GabrielMaida/CBtoPDF/blob/main/cb2pdf.py — reviewed source blob `adc7f5015be8856e9a8e972b33ead11e3a3d7460`, modified 2026-02-19. Its MIT notices, including copyright 2026 Gabriel Antônio Maida, are preserved in `LICENSE-fork`.

Snapshots were obtained through the GitHub connector; trailing newlines were normalized when writing local text files. Benchmark JSON records their SHA-256 digests. They are benchmark evidence, not application entry points. Never run these scripts in a directory containing valuable archives: their original behaviors include overwrites and moving sources. The harness isolates them against generated fixtures and suppresses only the upstream's import-time invocation before calling its batch function with zero artificial sleep.
