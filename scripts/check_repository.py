"""Data-independent syntax and local Markdown file-target checks."""
import ast
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def main():
    paths = subprocess.check_output(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
        cwd=ROOT).decode().split('\0')
    errors = []
    python_count = link_count = 0
    for name in sorted(set(paths) - {''}):
        path = ROOT / name
        if not path.is_file():
            continue
        if path.suffix == '.py':
            try:
                ast.parse(path.read_text(), filename=name)
                python_count += 1
            except SyntaxError as exc:
                errors.append(f'{name}: {exc}')
        if path.suffix == '.md':
            for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', path.read_text()):
                target = target.split('#')[0].strip('<>')
                if not target or '://' in target or target.startswith('mailto:'):
                    continue
                link_count += 1
                if not (path.parent / unquote(target)).exists():
                    errors.append(f'{name}: missing local link target {target}')
    print(f'Parsed {python_count} Python files; checked {link_count} local Markdown targets.')
    for error in errors:
        print(error)
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
