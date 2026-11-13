"""Convert Markdown files in docs/md to LaTeX fragments in docs/tex.

Usage:
    python src/convert_markdown_to_tex.py

Requires Pandoc. Existing output files are overwritten.
"""
from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO / "docs" / "md"
OUTPUT_DIR = REPO / "docs" / "tex"
ARCHIVE = REPO / "docs" / "tex.zip"  # gitignored; upload to Overleaf
# Not converted: references live in docs/tex/references.bib (hand-maintained).
SKIP = {"references.md"}


def archive_tex() -> None:
    """Zip docs/tex (files at the archive root) for upload to Overleaf."""
    with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUTPUT_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(OUTPUT_DIR))
    print(f"Archived {OUTPUT_DIR.relative_to(REPO)} -> {ARCHIVE.relative_to(REPO)}")


def main() -> None:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise SystemExit("Pandoc is required but was not found on PATH.")

    markdown_files = sorted(
        p for p in SOURCE_DIR.rglob("*.md") if p.name not in SKIP
    )
    if not markdown_files:
        print(f"No Markdown files found in {SOURCE_DIR}")
        archive_tex()
        return

    for source in markdown_files:
        output = OUTPUT_DIR / source.relative_to(SOURCE_DIR).with_suffix(".tex")
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                pandoc,
                "--from=markdown+tex_math_dollars",
                "--to=latex",
                "--natbib",  # [@key] -> \citep{key}, resolved by references.bib
                f"--output={output}",
                str(source),
            ],
            check=True,
        )
        print(f"{source.relative_to(REPO)} -> {output.relative_to(REPO)}")

    archive_tex()


if __name__ == "__main__":
    main()
