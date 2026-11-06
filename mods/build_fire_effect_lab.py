"""Build the separate, deterministic ESM-Z fire-effect identification package."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build():
    source = ROOT / 'mods/zat-fire-effect-lab'
    manifest = json.loads((source / 'mod.json').read_text())
    output = ROOT / 'dist/mods' / f"Zat-Fire-Effect-Lab-v{manifest['version']}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for file in sorted(source.rglob('*')):
            if not file.is_file():
                continue
            info = zipfile.ZipInfo(f"{manifest['id']}/{file.relative_to(source).as_posix()}", (2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, file.read_bytes())
        info = zipfile.ZipInfo(f"{manifest['id']}/src/config.defaults.lua", (2026, 10, 26, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, (source / 'src/config.lua').read_bytes())
    output.with_suffix('.zip.sha256').write_text(f'{hashlib.sha256(output.read_bytes()).hexdigest()}  {output.name}\n')
    print(output)
    return output


if __name__ == '__main__':
    build()
