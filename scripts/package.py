#!/usr/bin/env python3
"""Create a deterministic source ZIP with a per-file SHA-256 manifest."""
import argparse
import hashlib
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=root.parent / 'archguard-0.1.0.zip')
args = parser.parse_args()
excluded = {'target', '.validation', '.git', '__pycache__', '.idea'}
files = sorted(p for p in root.rglob('*') if p.is_file() and not excluded.intersection(p.relative_to(root).parts))
manifest = []
args.output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for path in files:
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        info = zipfile.ZipInfo('archguard/' + relative, date_time=(2026, 1, 1, 0, 0, 0))
        info.external_attr = 0o100644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(info, data)
        manifest.append(hashlib.sha256(data).hexdigest() + '  ' + relative)
    info = zipfile.ZipInfo('archguard/MANIFEST.sha256', date_time=(2026, 1, 1, 0, 0, 0))
    info.external_attr = 0o100644 << 16
    archive.writestr(info, '\n'.join(manifest) + '\n')
with zipfile.ZipFile(args.output) as archive:
    assert archive.testzip() is None
print(str(args.output.resolve()))
print('Files:', len(files) + 1)
print('SHA-256:', hashlib.sha256(args.output.read_bytes()).hexdigest())
