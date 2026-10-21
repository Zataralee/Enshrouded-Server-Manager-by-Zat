"""Build an isolated Python-required release without including local runtime data."""
import hashlib
import re
import shutil
import tempfile
import zipfile
from pathlib import Path


def build():
    app = Path(__file__).resolve().parent
    root = app.parent
    version = re.search(r'^APP_VERSION = "([^"]+)"', (app / "manager.py").read_text(), re.M)[1]
    output = root / "dist" / "versions"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="esm-release-") as temporary:
        stage = Path(temporary)
        target = stage / "enshrouded_manager"
        target.mkdir()
        for source in app.glob("*.py"):
            if not source.name.startswith("build_"):
                shutil.copy2(source, target / source.name)
        for name in ("README.md", "USER_README.md"):
            shutil.copy2(app / name, target / name)
        shutil.copytree(app / "static", target / "static")
        if version.endswith("b") and (app / "vendor").exists():
            shutil.copytree(app / "vendor", target / "vendor")
        shutil.copytree(root / "docs", stage / "docs", ignore=shutil.ignore_patterns("MODDING_VIABILITY_*.md"))
        shutil.copy2(root / "README.md", stage / "PROJECT_README.md")
        (stage / "Run ESM-Z.bat").write_text('@echo off\ncd /d "%~dp0"\npy -3 "%~dp0enshrouded_manager\\manager.py"\nif errorlevel 1 python "%~dp0enshrouded_manager\\manager.py"\npause\n')
        (stage / "README_FIRST.txt").write_text(
            f"ESM-Z v{version}\nRequires Windows and Python 3.11+.\n"
            "Run Run ESM-Z.bat, then open http://127.0.0.1:8080.\n"
            "For manual updates, stop ESM-Z and preserve enshrouded_manager/data.\n"
            "See docs/BETA_CHANNEL.md for beta switching and installation instructions.\n")
        archive = output / f"ESM-Z-PythonRequired-v{version}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
            for source in sorted(stage.rglob("*")):
                if source.is_file():
                    package.write(source, source.relative_to(stage).as_posix())
    legacy = output / f"EnshroudedServerManager-PythonRequired-v{version}.zip"
    shutil.copy2(archive, legacy)
    for package in (archive, legacy):
        digest = hashlib.file_digest(package.open("rb"), "sha256").hexdigest()
        package.with_suffix(".zip.sha256").write_text(f"{digest}  {package.name}\n", encoding="ascii")
    print(archive)


if __name__ == "__main__":
    build()
