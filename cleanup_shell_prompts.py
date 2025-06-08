#!/usr/bin/env python3
import pathlib
import re


def clean_file(path: pathlib.Path):
    text = path.read_text(encoding='utf-8-sig')
    cleaned = SHELL_PROMPT_PATTERN.sub('', text)
    if text != cleaned:
        path.write_text(cleaned, encoding='utf-8')
        print(f"[Cleaned] {path}")

def main():
    base = pathlib.Path(__file__).parent
    for py in base.rglob('*.py'):
        clean_file(py)

if __name__ == '__main__':
    main()
