# Development

Install the package and development extras in an activated virtual environment:

```sh
python -m pip install -e '.[rar,dev,benchmark]'
```

## Quality checks

```sh
python -m unittest discover -v
python -m mypy
python -m pyflakes src tests tools benchmarks/compare.py benchmarks/real_world.py benchmarks/performance.py cb2pdf.py
python -m pycodestyle --max-line-length=100 src tests tools benchmarks/compare.py benchmarks/real_world.py benchmarks/performance.py cb2pdf.py
python -m autopep8 --recursive --diff --exit-code --max-line-length=100 src tests tools
python -m autopep8 --diff --exit-code --max-line-length=100 benchmarks/compare.py benchmarks/real_world.py benchmarks/performance.py cb2pdf.py
python -m build
```

The 119-test unittest suite uses real archives/PDFs, exact image comparisons and
filesystem failure injection. RAR tests require the optional dependency and
appropriate native decoders. Poppler's optional `pdftoppm` independently renders
orientation cases. Missing optional tools produce explicit skips.

CI runs the quality checks, builds wheel/source artifacts, and tests the same
wheel outside the checkout across sixteen OS/Python/dependency configurations.
See [release validation](releasing.md) for installed-artifact reproduction.

## Repository layout

- `src/cb2pdf/`: conversion pipeline, public API and CLI.
- `tests/`: unit, integration, regression, security and failure tests.
- `tests/fixtures/rar/`: small synthetic archives with provenance and checksums.
- `tools/`: fixture generation and isolated installed-wheel validation.
- `benchmarks/`: workload generators, comparative runners and licensed references.
- `benchmarks/reports/`: retained final measurements and interpretation.
- `validation/`: final release evidence and the native decoder reproduction.
- `docs/`: user and maintainer guides.

Generated environments, work fixtures, logs, caches and build artifacts are
ignored. Private manga fixtures are never committed or included in source
archives. Keep current reports that substantiate compatibility, safety and
performance claims; superseded development runs remain accessible in Git history.

The historical benchmark scripts retain their original formatting and notices;
exclude them from application lint/format commands. Do not remove converter
features or safety checks as a housekeeping shortcut.
