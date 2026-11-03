#!/usr/bin/env python3
"""Compatibility launcher; importing from a source checkout loads the real package."""

import importlib.util
import sys
from pathlib import Path

source_package = Path(__file__).resolve().parent / "src"
if source_package.is_dir():
    sys.path.insert(0, str(source_package))

if __name__ == "cb2pdf":
    specification = importlib.util.spec_from_file_location(
        "cb2pdf", source_package / "cb2pdf" / "__init__.py",
        submodule_search_locations=[str(source_package / "cb2pdf")],
    )
    assert specification is not None and specification.loader is not None
    package = importlib.util.module_from_spec(specification)
    sys.modules[__name__] = package
    specification.loader.exec_module(package)
elif __name__ == "__main__":
    from cb2pdf.cli import main

    if len(sys.argv) == 1 and __spec__ is None:
        directory = Path(__file__).resolve().parent
        raise SystemExit(
            main(["convert", str(directory), "--move-original", str(directory / "old")]))
    raise SystemExit(main())
