"""Convert Markdown files in docs/md to LaTeX fragments in docs/tex.

Usage:
    python src/convert_markdown_to_tex.py

Requires Pandoc. Existing output files are overwritten.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO / "docs" / "md"
OUTPUT_DIR = REPO / "docs" / "tex"


def main() -> None:
    pandoc = shutil.which("pandoc")
    if pandoc is None:
        raise SystemExit("Pandoc is required but was not found on PATH.")

    markdown_files = sorted(SOURCE_DIR.rglob("*.md"))
    if not markdown_files:
        print(f"No Markdown files found in {SOURCE_DIR}")
        return

    for source in markdown_files:
        output = OUTPUT_DIR / source.relative_to(SOURCE_DIR).with_suffix(".tex")
        output.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                pandoc,
                "--from=markdown+tex_math_dollars",
                "--to=latex",
                f"--output={output}",
                str(source),
            ],
            check=True,
        )
        print(f"{source.relative_to(REPO)} -> {output.relative_to(REPO)}")


if __name__ == "__main__":
    main()
