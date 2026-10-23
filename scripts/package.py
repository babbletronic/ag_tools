"""Build installable and source ZIPs using only Python's standard library."""

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts"
OUTPUT.mkdir(exist_ok=True)

addon = OUTPUT / "old_shed_builder.zip"
with ZipFile(addon, "w", ZIP_DEFLATED) as archive:
    for path in sorted((ROOT / "old_shed_builder").rglob("*.py")):
        archive.write(path, path.relative_to(ROOT))
print(addon)

source = OUTPUT / "old_shed_builder_source.zip"
with ZipFile(source, "w", ZIP_DEFLATED) as archive:
    for folder in ("old_shed_builder", "scripts", "tests", "docs"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(ROOT))
    for name in ("README.md", ".gitignore"):
        archive.write(ROOT / name, name)
print(source)
