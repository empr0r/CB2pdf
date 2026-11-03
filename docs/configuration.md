# Configuration

There are two configuration sources: code defaults and explicit CLI options (or a `ConversionConfig` supplied through Python). There are no implicit environment overrides or configuration files. `TMPDIR`/`TEMP` follow the Python standard library's ordinary temporary-directory behavior.

## Conversion options

| Option | Behavior/default |
|---|---|
| positional inputs | One or more files/directories; files identified by signature |
| `--recursive` | Scan descendant directories, preserving relative output structure |
| `--output DIR` | PDF destination root; otherwise alongside each input |
| `--quality lossless/balanced/small` | Preserve / JPEG 90 / JPEG 75 plus 1600-pixel bounds |
| `--max-size N` or `WIDTHxHEIGHT` | Optional pixel bounds; preserve aspect ratio |
| `--upscale` | Allow enlargement; requires explicit max-size |
| `--jpeg-quality 1..100` | Balanced/small JPEG quality; rejected with lossless |
| `--flatten-alpha`, `--background RRGGBB` | Explicit flattening; default background white |
| `--dpi N` | Override image DPI for page layout, not stored pixel dimensions |
| `--page-size a4/letter` | Fixed displayed page size with image fitting |
| `--page-dimensions WIDTHxHEIGHT` | Fixed page size in integer PDF points; exclusive with page-size |
| `--frames all/reject` | Expand all image frames (default), or refuse multiframe images |
| `--ordering natural/lexical` | Natural default, documented in architecture |
| `--decode-verify` | Additionally decode pixels during inspection; more CPU/I/O |
| `--workers N` | Maximum active archive workers; default 1 |
| `--memory-budget-mb N` | Reduce workers using conservative per-worker estimates |
| `--fail-fast` | Cancel pending/active work cooperatively after the first failure |
| `--overwrite` | Explicit verified atomic replacement of existing PDFs |
| `--keep-original` | Default policy |
| `--move-original DIR` | Copy/commit/sync original there after PDF commit, then remove old name |
| `--dry-run` | Inspect and plan without persistent PDFs, reports, file logs or archival |
| `--title`, `--author`, `--subject`, `--keywords ...` | Optional PDF metadata; creator is CB2pdf |
| `--report FILE` | Exclusive JSON outcome report including every page's transformations |
| `--verbose` / `--quiet` | Debug logging / errors only |
| `--log-file FILE`, `--json-logs` | Exclusive UTF-8 file log / JSON log records |

Dry-run is not a complete conversion simulation: it does not perform image encoding, PDF generation, final verification or commit checks. Small profile settings authorize resizing/lossy encoding; an explicitly resized lossless-profile conversion is lossless in its subsequent encoding, not pixel-identical to the source.

## Resource ceilings

Every ceiling below is available as its hyphenated CLI flag, e.g. `--max-pixels 20000000`. Byte values are integer bytes, not MiB.

| Configuration field | Default |
|---|---:|
| `max_members` | 10,000 |
| `max_pages` | 10,000 |
| `max_member_bytes` | 134,217,728 (128 MiB) |
| `max_total_bytes` | 4,294,967,296 (4 GiB) |
| `max_compression_ratio` | 1,000 |
| `max_pixels` | 40,000,000 per frame |
| `max_pdf_input_bytes` | 536,870,912 (512 MiB) |
| `max_output_bytes` | 2,147,483,648 (2 GiB) |

ZIP/RAR metadata is additionally capped at 16 MiB; member names at 4096 characters. RAR parsing allows up to 100 extra service headers beyond the member ceiling. Declared size/ratio limits cover all entries; actual EOF/CRC checks apply to selected image data. PDF input accounting charges exact direct-stream input sizes, or a conservative eight bytes per pixel for non-direct encoding, whichever is larger. This prevents tiny compressed inputs bypassing retained-image budgeting. Pillow's own bomb protections remain active even if custom pixel limits are increased.

The estimated worker envelope is `3 * max_pdf_input_bytes + 16 * max_pixels + 2 * max_member_bytes`. A supplied memory budget below one estimated worker is rejected. This reduces concurrency; it is not an OS-enforced memory limit. Library temporaries, allocation behavior and Python GC can affect actual peak RSS. Native RAR/decoder timeouts are not enforced.

## Status and exit codes

JSON statuses distinguish `success`, `failed`, `cancelled`, `dry_run`, `pdf_committed_archival_incomplete` and `pdf_committed_durability_failed`. Check `verified`, `committed`, `source_retained`, `archived_to`, `error_type`, `error`, and page transformations to understand partial outcomes. Skipped pages are always zero: a required invalid page fails conversion.

Exit 0: requested work succeeded (including valid dry-run). Exit 1: conversion failures, cancellations or no comic archives found. Exit 2: argument/preflight/inspection/reporting errors. Exit 130: interruption. Already committed PDFs remain available after interruption or a later batch failure.

## Performance implementation and accounting

`--workers` controls active archives. Each active archive may also use one native SHA-256 helper thread, and at most two digest payloads can be outstanding. The measured threshold is 256 KiB; smaller payloads remain synchronous. This changes CPU overlap, not the required digest checks. Conversion waits for all input digests, verification waits for all output digests, and publication remains synced and exclusive. The existing memory estimate includes room for member buffers; it remains a conservative scheduling estimate rather than an OS cap.

Opaque non-interlaced PNG validation inflates into blocks of at most 1 MiB, checks scanline/filter structure, and discards those blocks without reconstructing RGB pixels. Invalid compressed streams or expansion beyond IHDR dimensions fail the archive. PNG metadata chunks over 16 MiB are rejected; Pillow's own text-decompression safeguards remain active. Late color/transparency/DPI chunks are refused rather than silently ignored by the embedding library. Late EXIF is tolerated for compatibility with existing files.
