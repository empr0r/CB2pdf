# Synthetic compressed RAR fixtures

The four format/compression archives contain only three generated test images, licensed with
the project's MIT license. No manga, user documents or archiver binaries are
included. Each format has ordinary compression and solid compression. BMP pages
ensure actual RAR compression is exercised; PNG and deliberately unpadded names
also exercise mixed image handling and natural page ordering. A fifth archive contains literal bracket/dollar/parenthesis names and a nearby nonliteral match, protecting bsdtar selectors from glob confusion.

Generated using RAR 6.24 (official Linux evaluation distribution) with
`tools/make_rar_fixtures.py`. The archiver was downloaded separately from
https://www.rarlab.com/rar/rarlinux-x64-624.tar.gz, SHA-256
`88e22a8e84125c947637bbf28c746e338a0a63279d80f9f9d7373603875db1eb`.
It is not an application dependency and is not redistributed. Creating new RAR
archives requires a separately licensed/evaluation archiver; running these tests
requires only rarfile and a compatible decoder.

Regenerate equivalent fixtures in a new directory with a tool supporting both
`-ma4` and `-ma5`:

```sh
python tools/make_rar_fixtures.py --rar /path/to/rar --output /tmp/new-rar-fixtures
```

`manifest.json` records exact archive and uncompressed member SHA-256 identities.
Archiver versions/platforms may produce different archive bytes; review changes
and regenerate the manifest together. Tests verify actual compression, solid
flags, output pixels/order, source retention, corruption failures and limits. Bsdtar's unsupported solid RAR4 case must report MissingDependencyError and preserve the source.
Decoder-specific tests run when that executable is available; unavailable
decoders produce explicit unittest skips.
