"""Check publishable source without displaying credentials or reading local data."""
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '.venv', 'venv', 'node_modules', 'dist', 'instance', '__pycache__', '.pytest_cache', '.vscode', '.aws', '.codex', 'release', 'coverage', 'htmlcov'}
PRIVATE_SUFFIXES = {'.pem', '.key', '.p12', '.pfx', '.eml', '.db', '.sqlite', '.zip', '.log'}
PATTERNS = [re.compile(value) for value in (
    r'\bsk_live_[A-Za-z0-9]{20,}', r'\bgh[pousr]_[A-Za-z0-9]{30,}',
    r'\bAKIA[A-Z0-9]{16}\b', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
)]


def source_files():
    if (ROOT / '.git').exists():
        # Include tracked files even when an ignore rule would hide a leak.
        result = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                                cwd=ROOT, check=True, capture_output=True)
        return [ROOT / item.decode('utf-8') for item in result.stdout.split(b'\0') if item]
    paths = []
    for folder, directories, files in os.walk(ROOT):
        directories[:] = [name for name in directories if name not in SKIP]
        for name in files:
            if name == '.env' or (name.startswith('.env.') and name != '.env.example'):
                continue
            path = Path(folder) / name
            if path.suffix.lower() in PRIVATE_SUFFIXES or name.endswith(('-results.json', '-results.xml', '.tar.gz')):
                continue
            paths.append(path)
    return paths


def main():
    failures = []
    for path in source_files():
        relative = path.relative_to(ROOT)
        if not path.is_file():
            continue
        private = (any(part in SKIP for part in relative.parts) or path.name == '.env'
                   or (path.name.startswith('.env.') and path.name != '.env.example')
                   or path.suffix.lower() in PRIVATE_SUFFIXES)
        if private:
            failures.append(f'Private/generated file selected for publication: {relative}')
            continue
        if path.stat().st_size > 2_000_000:
            continue
        content = path.read_text(encoding='utf-8', errors='replace')
        if any(pattern.search(content) for pattern in PATTERNS):
            failures.append(f'Possible credential in source: {relative}')
    if failures:
        raise SystemExit('\n'.join(failures))
    print('Release source check passed; no local account data or detected credentials selected.')


if __name__ == '__main__':
    main()
