"""Verify ordered Release parts and reconstruct the original offline archive."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parts-dir', type=Path, default=Path('.'))
    ap.add_argument('--output-dir', type=Path)
    args = ap.parse_args()
    manifest = json.loads((args.parts_dir/'manifest.json').read_text())
    destination = (args.output_dir or args.parts_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    assert Path(manifest['archive']).name == manifest['archive']
    output = destination/manifest['archive']
    if output.exists():
        raise SystemExit('Output already exists; verify it with sha256sum instead of overwriting.')
    if shutil.disk_usage(destination).free < manifest['bytes']+1024**3:
        raise SystemExit('Insufficient free space to reconstruct the archive.')
    for part in manifest['parts']:
        assert Path(part['name']).name == part['name']
        path = args.parts_dir/part['name']
        if not path.exists() or path.stat().st_size != part['bytes']:
            raise SystemExit('Missing or incomplete part: '+str(path))
    temporary = output.with_suffix(output.suffix+'.partial')
    if temporary.exists():
        raise SystemExit('A previous partial output exists; inspect it before retrying.')
    total_hash = hashlib.sha256()
    total_bytes = 0
    with temporary.open('xb') as out:
        for part in manifest['parts']:
            part_hash = hashlib.sha256()
            with (args.parts_dir/part['name']).open('rb') as src:
                for block in iter(lambda:src.read(8*1024**2), b''):
                    out.write(block)
                    part_hash.update(block)
                    total_hash.update(block)
                    total_bytes += len(block)
            if part_hash.hexdigest() != part['sha256']:
                raise SystemExit('Part checksum mismatch: '+part['name'])
            print('VERIFIED', part['name'], flush=True)
        out.flush()
        os.fsync(out.fileno())
    assert total_bytes == manifest['bytes']
    assert total_hash.hexdigest() == manifest['sha256'], 'Overall checksum mismatch'
    temporary.rename(output)
    print('RESTORED', output, total_bytes, total_hash.hexdigest(), flush=True)


if __name__ == '__main__':
    main()
