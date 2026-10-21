"""Build a deterministic ESM-Z-compatible EML upload ZIP; no game files included."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "mods" / "zat-shock-tuning"


def build():
    manifest = json.loads((SOURCE / "mod.json").read_text(encoding="utf-8"))
    destination = ROOT / "dist" / "mods" / f"Zat-Shock-Tuning-v{manifest['version']}.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = ["mod.json", "src/mod.lua", "src/config.lua", "README.txt", "VALIDATION.txt", "LICENSE.txt"]
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files:
            info = zipfile.ZipInfo(f"{manifest['id']}/{name}", date_time=(2026, 10, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (SOURCE / name).read_bytes())
        info = zipfile.ZipInfo(f"{manifest['id']}/src/config.defaults.lua", date_time=(2026, 10, 21, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, (SOURCE / "src/config.lua").read_bytes())
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(".zip.sha256").write_text(f"{checksum}  {destination.name}\n", encoding="ascii")
    print(destination)
    return destination


if __name__ == "__main__":
    build()
