# CB2pdf 2.0.0 engineering delivery

The final stable build passed all eighteen CI jobs: sixteen installed-artifact
configurations, build/strict package metadata checks, and quality checks.
[Run 41763768811](https://github.com/empr0r/CB2pdf/actions/runs/41763768811)
tested commit `22b2beb1d2a23304f8ec0593dc67049ecbb00a6d`.
The exact CI-built wheel and source archive are retained locally, with SHA256SUMS,
under `dist/2.0.0/ci-tested/`. Publication, remote tags and default-branch merging
have not been performed.

## Architecture and functionality

| Responsibility | Components |
|---|---|
| Validated policies and outcomes | `config.py`, `models.py`, `errors.py` |
| Signature detection, limits and archive streams | `archives.py`, `rar_backend.py` |
| Deterministic member/page ordering | `ordering.py` |
| Image inspection, bounded PNG validation and conditional normalization | `images.py`, `png.py` |
| Bounded native hashing | `digests.py` |
| Image embedding, layout and independent verification | `pdf.py` |
| Exclusive atomic publication and separate source archival | `transactions.py` |
| Conversion sequencing and bounded batch execution | `converter.py`, `scheduler.py` |
| CLI, logging, reports and reproducible workloads | `cli.py`, `reporting.py`, `benchmark.py` |

The application converts CBZ/ZIP and supported CBR/RAR variants, with natural
ordering, nested/Unicode member names, six image format families, frame/page
expansion, EXIF orientation, transparency handling, optional resizing/layout/DPI,
quality profiles and document metadata. CLI commands support individual files,
recursive batches, inspection, dry runs, bounded workers, JSON reports/logs,
explicit overwrite and optional source archival. The compatibility launcher
retains its documented move-to-old workflow; ordinary conversion keeps originals.

## Preservation and safety

Compatible JPEG/PNG representation is embedded directly; resolution is retained
by default. Required normalization is isolated and transformations are reported.
Lossy profiles/resizing are explicit choices. Image/member/page/document budgets,
archive name/link/encryption checks, CRCs and bounded PNG stream validation remain
enabled. Archive members are not extracted under their input names.

PDF output uses an owned target-filesystem temporary, fsync, independent strict
parsing, expected page counts/dimensions/rotation/resources and direct-stream
SHA-256/order checks before publication. Default publication is exclusive; source
archival starts only after PDF commit. Partial durability/archival outcomes remain
explicit. Failure tests cover existing-output races, source mutation, corrupt
images/archives, missing/reordered pages, interrupted writes and archival failures.

The RAR adapter fixes bsdtar command ordering, protects literal member selectors,
rejects its unsupported solid-RAR4 case clearly and checks enabled 7-Zip methods.
Real tests distinguish missing methods from native crashes. The Linux CI binary
is upstream 7-Zip 26.05 with a pinned archive SHA-256; the crashing Ubuntu package
pair is retained as reproduction evidence. Native extraction assertions were
not weakened to hide that failure.

## Measured performance

The dedicated performance comparison measured commit `fd1dc7f` against its frozen
pre-optimization package and the retained fork, with five randomized fresh-process
trials per variant/workload. In five synthetic workloads with complete,
pixel-identical outputs, its medians were 1.19×–1.99× faster than the fork.
Large-JPEG maximum RSS fell from baseline 417.4 to 268.5 MiB; several-large-volume
RSS fell from 395.1 to 167.6 MiB. One 184-page real fixture retained a 6.4 ms fork
median lead while using 99.0 versus 159.7 MiB in the redesign.

Those measurements used the dependency versions recorded in their JSON; they
predate the final CBR diagnostics and dependency updates. They are historical
workload evidence, not a new universal timing claim for this stable release.
See [performance report](../../benchmarks/reports/performance-summary.md).
The optimization retains strict verification/durability, removes duplicate PNG
raster reconstruction and ZIP growth buffers, overlaps bounded hashes with I/O,
and releases the owned PDF graph before verification. Processing is not
constant-memory and native CPU overlap does not imply lower total CPU cost.

## Testing and compatibility

The final CI suite discovered 119 tests in each installed-artifact job:
**1,855 executed tests passed**, 49 expected decoder/renderer skips, zero
failures/errors. All jobs tested the same wheel, checking installed files against
its contents outside the source checkout. Every job also passed version and
exact six-page pixel/JPEG-stream smoke checks.

| Platform | Configurations | Outcome |
|---|---|---|
| Linux | Python 3.11–3.14/latest, 3.11/minimum, 3.14/basic | 6 passed |
| Windows | Python 3.11–3.14/latest, 3.11/minimum | 5 passed |
| macOS | Python 3.11–3.14/latest, 3.11/minimum | 5 passed |

The 49 skips are explicit: unavailable optional rarfile in the basic install
(14), missing unar/unrar/bsdtar executables in dedicated backend cases (30),
and unavailable Windows Poppler rendering (5). They do not silently skip pages.
Linux/macOS independently render all eight orientation modes. Windows executes
the remaining image/PDF, native 7-Zip and filesystem/publication tests.

Six additional local stable-wheel environments passed 695 executed tests with
19 expected skips. The exact delivered CI wheel was separately installed and
smoke-tested on the local basic environment. Strict Twine, mypy (18 source
files), pyflakes, pycodestyle, autopep8, compilation, Python 3.11 grammar,
actionlint, dependency consistency and package-content checks passed. The CI
wheel equals current runtime source; the source archive matches 82 current
repository files and excludes private work and audit-only records.

Latest resolved runtime versions were Pillow 13.0.0, img2pdf 0.6.3,
pypdf 6.21.4, pikepdf 10.17.0 and rarfile 4.5. The tested explicit floor is
Pillow 10.4.0, img2pdf 0.6.3, pypdf 6.12.0 and rarfile 4.2 on Python 3.11.
Raw reports retain each job's exact OS/runtime/dependency and decoder identities.

## Known limitations and next work

- Exclusive no-overwrite publication requires hard-link support. Other
  filesystems fail safely; Windows directory durability has platform limits.
- Native decoding/resource estimates and cooperative cancellation are not hard
  OS-enforced memory/time isolation. External codecs can contain bugs; sources
  remain intact on controlled conversion failure.
- Encrypted, split/multivolume and self-extracting archives are unsupported.
- Gamma/arbitrary metadata, animation timing, unusual color/high-depth samples
  and extreme-size documents require broader preservation-corpus validation.
  Unsupported sample types fail explicitly; a pixel-perfect rendering of every
  original metadata combination is not claimed.
- Default JPEG inspection checks headers; `--decode-verify` adds pixel decoding.
  No standalone executable is distributed.

Prioritize broader color-managed/large-document tests, native process isolation
and ongoing decoder/library security updates. Publishing should use the exact
reviewed artifacts and tested commit after explicit approval; it should not
substitute an untested rebuild. Repository audit-only evidence is kept separately
from distribution inputs, so recording these results does not change the
qualified application or release bytes.
