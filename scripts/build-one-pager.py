#!/usr/bin/env python3
"""Build the tracked print guide and refuse accidental multi-page output."""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]


def main():
    render = runpy.run_path(str(ROOT / 'scripts/build-release.py'))['pdf_guide']
    document = render((ROOT / 'docs/one-page-guide.md').read_text())
    pages = document.count(b'/Type /Page ')
    if pages != 1:
        raise SystemExit(f'Guide expanded to {pages} pages; shorten it before publishing.')
    output = ROOT / 'docs/Codex-Workbench-One-Page.pdf'
    output.write_bytes(document)
    print(output)


if __name__ == '__main__':
    main()
