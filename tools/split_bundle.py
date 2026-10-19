"""Split the verified archive into GitHub Release assets; never alter it."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('archive', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--sha256', required=True)
    ap.add_argument('--part-bytes', type=int, default=1024**3)
    args = ap.parse_args()
    assert 0 < args.part_bytes < 2*1024**3
    args.output.mkdir(parents=True, exist_ok=True)
    marker = args.output/'manifest.json'
    if marker.exists():
        m = json.loads(marker.read_text())
        assert m['sha256'] == args.sha256
        for p in m['parts']:
            path = args.output/p['name']
            assert path.stat().st_size == p['bytes']
        print('SPLIT_ALREADY_COMPLETE', len(m['parts']), flush=True)
        return
    assert shutil.disk_usage(args.output).free > args.archive.stat().st_size+2*1024**3
    overall = hashlib.sha256()
    parts = []
    with args.archive.open('rb') as src:
        index = 0
        while True:
            first = src.read(min(8*1024**2, args.part_bytes))
            if not first:
                break
            name = f'{args.archive.name}.part-{index:03d}'
            final = args.output/name
            temporary = final.with_suffix(final.suffix+'.partial')
            part_hash = hashlib.sha256()
            total = 0
            with temporary.open('wb') as out:
                block = first
                while block:
                    out.write(block)
                    overall.update(block)
                    part_hash.update(block)
                    total += len(block)
                    block = src.read(min(8*1024**2, args.part_bytes-total)) if total < args.part_bytes else b''
            temporary.rename(final)
            parts.append(dict(name=name, bytes=total, sha256=part_hash.hexdigest()))
            print('PART_READY', name, total, flush=True)
            index += 1
    assert overall.hexdigest() == args.sha256, 'Source archive checksum mismatch'
    payload = dict(schema=1, archive=args.archive.name, bytes=args.archive.stat().st_size,
                   sha256=args.sha256, part_bytes=args.part_bytes, parts=parts)
    marker.write_text(json.dumps(payload, indent=2))
    (args.output/'SHA256SUMS.parts').write_text(''.join(f"{p['sha256']}  {p['name']}\n" for p in parts))
    (args.output/(args.archive.name+'.sha256')).write_text(f'{args.sha256}  {args.archive.name}\n')
    print('SPLIT_COMPLETE', len(parts), payload['bytes'], payload['sha256'], flush=True)


if __name__ == '__main__':
    main()
