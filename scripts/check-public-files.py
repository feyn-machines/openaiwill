"""Check tracked public files without printing potential secret values."""
import pathlib
import re
import subprocess
import sys

private_parts = {'.agents', '.claude', '.codex', '.lawrence', '.opencode', 'skills', '.venv', 'cookies', 'data'}
patterns = [r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', r'\bgh[pousr]_[A-Za-z0-9]{30,}', r'\bgithub_pat_[A-Za-z0-9_]{30,}', r'\bsk-[A-Za-z0-9_-]{24,}', r'https?://[^\s/:]+:[^\s/@]+@']
failures = []
files = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
for name in filter(None, files):
    path = pathlib.PurePosixPath(name)
    if private_parts.intersection(path.parts) or path.name in {'AGENTS.md', 'CLAUDE.md'} or path.name.startswith('.env') or path.suffix in {'.pem', '.key', '.p12', '.pfx'} or 'cookies' in path.name.lower():
        failures.append(f'{name}: private file')
    data = subprocess.check_output(['git', 'show', ':' + name]).decode(errors='replace')
    if any(re.search(pattern, data) for pattern in patterns):
        failures.append(f'{name}: possible credential')
if failures:
    print('\n'.join(failures))
    sys.exit(1)
print(f'Public-file check passed ({len(list(filter(None, files)))} tracked files).')
