# Initial engineering assessment

The requested upstream, https://github.com/empr0r/CB2pdf, contains LICENSE, README.md and one script. The reviewed head was `19bc5a2cc09bfa58de98d3e0b20ab8e663dccd49`; the four visible commits introduce the MIT license, script and README, then two documentation updates. There were no tests, packaging files, CI, or package boundaries.

The pre-existing local checkout at `Documents/GitHub/CBZ-to-pdf` is a different older project and was left untouched. Direct Git/pip network access failed DNS resolution. The requested repository was imported into `Projects/CB2pdf` from the connected GitHub reader, with an explicit local snapshot commit. This local history is not a full Git clone. The GitHub reader was also used to obtain external dependency source for local validation; none of those dependency source trees is included in the application.

Confirmed upstream defects:

- `process_cbz`/`process_cbr` catch exceptions without returning a success indicator. `process_file` unconditionally moves the original afterward, including failed or empty conversions.
- Existing PDFs are opened for replacement without collision protection, verification, or atomic publication.
- Pillow converts every page to RGB and saves through its PDF encoder. JPEG representations are not retained; the source comment claiming no quality reduction is inaccurate.
- All decoded pages remain in memory until output is saved. Threaded volumes amplify this cost.
- Lexical sorting misorders numeric filenames. Archive selection depends only on the filename extension.
- There are no archive/image resource ceilings, encryption policy, multipage policy, or systematic error/status contracts.
- Fixed batches, sleep intervals, and unconditional garbage collection are not performance measurements.

The reference fork at https://github.com/GabrielMaida/CBtoPDF improves natural sorting, img2pdf embedding, format coverage, logging, extraction isolation, and explicit success handling. Source review also confirms full extraction, automatic 2560-pixel bounds, JPEG quality-90 normalization, same-stem temporary JPEG collisions, whole-PDF byte buffering, overwrites, silent skipping of invalid images, sequential processing, and no independent output verification. Its `.tiff` suffix list omits `.tif`.

Implementation boundaries: validated configuration and result/error models; checked archive readers; deterministic ordering; image inspection/lazy normalization; PDF writing/verification; filesystem transactions; bounded archive scheduling; CLI/reporting; fixture/benchmark infrastructure. These separate ownership, invariants and failure boundaries without creating empty architectural layers.

Risks identified before implementation were PDF-library memory retention, flipped EXIF orientations, animated/multiframe decoding, native RAR limitations, output races, and filesystem durability. Tests use actual archive/PDF operations, SHA-256 and decoded-pixel checks, optional renderer checks, and targeted fault injection. Benchmarks use identical deterministic inputs, fresh worker processes, repeated trials, separate fidelity/completeness validation, and explicit distinction between historical lossy defaults and current preservation defaults.

After the initial work, the user's clean clone became available at `Documents/GitHub/CB2pdf`. The completed changes were transferred onto its original upstream history on branch `operation-condor`, and the test suite was rerun there. That clone is now canonical; the Projects workspace remains an audit copy of the initial snapshot workflow and private test artifacts.
