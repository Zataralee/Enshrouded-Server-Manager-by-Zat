"""Fetch the original EML release for beta packaging (never modifies the binary)."""
import hashlib
from pathlib import Path
import urllib.request


def prepare():
    root = Path(__file__).resolve().parent / "vendor" / "eml-v0.2.0"
    root.mkdir(parents=True, exist_ok=True)
    assets = {
        "emm.exe": "https://github.com/Brabb3l/kfc-parser/releases/download/v0.2.0/emm.exe",
        "LICENSE": "https://raw.githubusercontent.com/Brabb3l/kfc-parser/v0.2.0/LICENSE",
        "source-v0.2.0.zip": "https://api.github.com/repos/Brabb3l/kfc-parser/zipball/v0.2.0",
    }
    for name, url in assets.items():
        target = root / name
        if not target.is_file():
            request = urllib.request.Request(url, headers={"User-Agent": "ESM-Z-build"})
            with urllib.request.urlopen(request, timeout=90) as response:
                target.write_bytes(response.read())
    with (root / "emm.exe").open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    if checksum != "b1133f6b8ea7000596cc7710901bd8307b48165b0e650c0487a611d90ea49305":
        raise RuntimeError("Upstream EML binary checksum mismatch")


if __name__ == "__main__":
    prepare()
