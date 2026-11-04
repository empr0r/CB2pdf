"""Regenerate small synthetic RAR4/RAR5 fixtures with a separately installed RAR.

The archiver is test tooling, not a runtime dependency or redistributed component.
Outputs contain only application-generated pixels. Existing fixtures are protected.
"""

import argparse
import hashlib
import io
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image


def generate(executable: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    names = [f"rar{version}-{mode}.cbr"
             for version in (4, 5) for mode in ("compressed", "solid")]
    protected = [*names, "special-names.cbr", "manifest.json"]
    if any((destination / name).exists() for name in protected):
        raise FileExistsError("choose an empty fixture destination")
    manifest = {"generator": "tools/make_rar_fixtures.py", "archives": {}, "members": {}}
    with tempfile.TemporaryDirectory(prefix="cb2pdf-rar-fixtures-") as temporary:
        source = Path(temporary)
        (source / "chapter").mkdir()
        for index, name in enumerate(("page1.bmp", "page2.bmp", "page10.png")):
            with Image.new("RGB", (64, 96)) as image:
                image.putdata([
                    ((x * 7 + index * 40) % 256, (y * 3 + index * 30) % 256,
                     ((x // 8 + y // 8) % 2) * 180)
                    for y in range(96) for x in range(64)
                ])
                buffer = io.BytesIO()
                image.save(buffer, format="PNG" if name.endswith("png") else "BMP")
            data = buffer.getvalue()
            member = "chapter/" + name
            (source / member).write_bytes(data)
            manifest["members"][member] = hashlib.sha256(data).hexdigest()
        for version in (4, 5):
            for mode in ("compressed", "solid"):
                name = f"rar{version}-{mode}.cbr"
                target = destination.resolve() / name
                command = [executable, "a", f"-ma{version}", "-m5", "-md1m", "-mt1",
                           "-s" if mode == "solid" else "-s-", "-ep1", "-ts-", "-idq",
                           str(target), "chapter"]
                subprocess.run(command, cwd=source, check=True, timeout=60)
                manifest["archives"][name] = hashlib.sha256(target.read_bytes()).hexdigest()
        special = {}
        originals = [(source / "chapter/page1.bmp").read_bytes(),
                     (source / "chapter/page2.bmp").read_bytes()]
        for name, data in zip(("-cover[1]$(ignored).bmp", "-cover1$(ignored).bmp"),
                              originals, strict=True):
            member = "selectors/" + name
            (source / "selectors").mkdir(exist_ok=True)
            (source / member).write_bytes(data)
            special[member] = hashlib.sha256(data).hexdigest()
        target = destination.resolve() / "special-names.cbr"
        subprocess.run([executable, "a", "-ma5", "-m5", "-md1m", "-mt1", "-s-", "-ts-",
                        "-idq", str(target), "selectors"], cwd=source, check=True, timeout=60)
        manifest["special_names"] = {
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "members": special,
        }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rar", required=True, help="RAR executable supporting -ma4 and -ma5")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate(str(Path(args.rar).resolve()), args.output)


if __name__ == "__main__":
    main()
