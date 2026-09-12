import hashlib
import re
import shutil
import tarfile
import tempfile
from pathlib import Path


MANAGER_DIR = Path(__file__).resolve().parent
ROOT = MANAGER_DIR.parent
RELEASE_DIR = ROOT / "release"
VERSION_MATCH = re.search(r'^APP_VERSION = "([^"]+)"', (MANAGER_DIR / "manager.py").read_text(encoding="utf-8"), re.MULTILINE)
if not VERSION_MATCH:
    raise RuntimeError("Could not read APP_VERSION from manager.py")

VERSION = VERSION_MATCH.group(1)
PACKAGE_NAME = f"ESM-Z-Linux-PythonRequired-v{VERSION}"
OUTPUT = RELEASE_DIR / f"{PACKAGE_NAME}.tar.gz"
CHECKSUM = OUTPUT.with_suffix(OUTPUT.suffix + ".sha256")


def add_tree(archive, source, destination):
    archive.add(source, arcname=destination, filter=archive_filter)


def archive_filter(info):
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mode = 0o755 if info.isdir() or info.name.endswith(".sh") else 0o644
    return info


RELEASE_DIR.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as temporary:
    stage = Path(temporary) / PACKAGE_NAME
    packaged_manager = stage / "enshrouded_manager"
    packaged_manager.mkdir(parents=True)
    shutil.copy2(MANAGER_DIR / "manager.py", packaged_manager / "manager.py")
    shutil.copytree(MANAGER_DIR / "static", packaged_manager / "static")
    shutil.copy2(MANAGER_DIR / "README.md", packaged_manager / "README.md")
    shutil.copy2(MANAGER_DIR / "USER_README.md", packaged_manager / "USER_README.md")
    launcher = (MANAGER_DIR / "Run ESM-Z.sh").read_text(encoding="utf-8")
    (stage / "Run ESM-Z.sh").write_text(launcher, encoding="utf-8", newline="\n")
    shutil.copy2(ROOT / "README.md", stage / "PROJECT_README.md")
    shutil.copytree(ROOT / "docs", stage / "docs")
    shutil.copy2(ROOT / "docs" / "LINUX_ALPHA.md", stage / "README_FIRST.md")

    with tarfile.open(OUTPUT, "w:gz") as archive:
        add_tree(archive, stage, PACKAGE_NAME)

digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
CHECKSUM.write_text(f"{digest}  {OUTPUT.name}\n", encoding="ascii")
print(f"Created {OUTPUT}")
print(f"SHA-256 {digest}")
