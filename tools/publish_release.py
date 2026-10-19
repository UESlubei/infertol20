"""Resumable upload of the offline environment as verified GitHub Release assets.

Requires gh authentication; no token is read or printed by this script.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import threading
import time


def run(args, missing_ok=False):
    p = subprocess.run(['gh', *args], capture_output=True, text=True)
    if p.returncode:
        if missing_ok and '(HTTP 404)' in p.stderr:
            return None
        raise RuntimeError(p.stderr.strip() or p.stdout.strip())
    return p.stdout


def api(path, missing_ok=False):
    output = run(['api', path], missing_ok=missing_ok)
    return json.loads(output) if output is not None else None


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda:stream.read(8*1024**2), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--assets-dir', type=Path, required=True)
    ap.add_argument('--notes-file', type=Path, required=True)
    ap.add_argument('--target', required=True)
    ap.add_argument('--state-dir', type=Path, required=True)
    ap.add_argument('--repo', default='UESlubei/infertol20')
    ap.add_argument('--tag', default='v3-rtx3090-offline-20261019')
    args = ap.parse_args()
    run(['auth', 'status', '--hostname', 'github.com'])
    repo = api('repos/'+args.repo)
    assert repo['permissions']['push'], 'Authenticated account cannot push to the target repository.'
    manifest = json.loads((args.assets_dir/'manifest.json').read_text())
    expected = {p['name']:{'size':p['bytes'], 'sha256':p['sha256']} for p in manifest['parts']}
    for name in ['manifest.json', 'SHA256SUMS.parts', manifest['archive']+'.sha256',
                 'restore_bundle.py', 'README_迁移操作.md']:
        path = args.assets_dir/name
        expected[name] = {'size':path.stat().st_size, 'sha256':sha(path)}
    for name, info in expected.items():
        assert Path(name).name == name
        assert (args.assets_dir/name).stat().st_size == info['size']
        assert info['size'] < 2*1024**3
    endpoint = f'repos/{args.repo}/releases/tags/{args.tag}'
    release = api(endpoint, missing_ok=True)
    if release is None:
        print('CREATE_DRAFT', args.tag, args.target, flush=True)
        run(['release', 'create', args.tag, '--repo', args.repo, '--draft',
             '--target', args.target, '--title', 'vLLM KV 调度 V3：RTX 3090 离线迁移包',
             '--notes-file', str(args.notes_file)])
        release = api(endpoint)
    release_id = release['id']
    args.state_dir.mkdir(parents=True, exist_ok=True)
    state = dict(repo=args.repo, tag=args.tag, release_url=release['html_url'],
                 target_commit=args.target, total_assets=len(expected), assets={}, state='uploading')
    lock = threading.Lock()

    def save():
        path = args.state_dir/'upload_status.json'
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2))
        temp.replace(path)

    def verify(asset, info):
        if asset['size'] != info['size'] or asset['state'] != 'uploaded':
            return False
        digest = asset.get('digest')
        if digest and digest != 'sha256:'+info['sha256']:
            raise RuntimeError('Remote digest mismatch: '+asset['name'])
        return True

    def upload(name, info):
        for attempt in range(1, 4):
            remote = {a['name']:a for a in api(endpoint)['assets']}
            asset = remote.get(name)
            if asset and verify(asset, info):
                with lock:
                    state['assets'][name] = {'id':asset['id'],'bytes':asset['size'],
                                            'digest':asset.get('digest'),'verified':True}
                    save()
                print('ASSET_VERIFIED', name, asset['size'], flush=True)
                return
            if asset:
                if release['draft'] and asset['state'] == 'starter' and asset['size'] == 0:
                    run(['api', '--method', 'DELETE', f'repos/{args.repo}/releases/assets/{asset["id"]}'])
                else:
                    raise RuntimeError('An existing asset differs; refusing to replace it: '+name)
            print('UPLOAD_START', name, 'attempt', attempt, flush=True)
            proc = subprocess.run(['gh','release','upload',args.tag,str(args.assets_dir/name),
                                   '--repo',args.repo], capture_output=True, text=True)
            if proc.returncode:
                print('UPLOAD_RETRY', name, proc.stderr[-1500:], flush=True)
                time.sleep(2**attempt)
            else:
                print('UPLOAD_FINISHED', name, flush=True)
        # Verify after the final successful upload too.
        asset = next((a for a in api(endpoint)['assets'] if a['name']==name), None)
        if not asset or not verify(asset, info):
            raise RuntimeError('Asset upload did not complete: '+name)
        with lock:
            state['assets'][name] = {'id':asset['id'],'bytes':asset['size'],
                                    'digest':asset.get('digest'),'verified':True}
            save()

    save()
    try:
        # Small instructions and manifests are uploaded first. All assets remain
        # in a draft until every part has completed verification.
        ordered = sorted(expected, key=lambda n:expected[n]['size'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(upload, n, expected[n]) for n in ordered]
            for future in as_completed(futures):
                future.result()
        remote = api(endpoint)
        indexed = {a['name']:a for a in remote['assets']}
        assert all(n in indexed and verify(indexed[n], info) for n,info in expected.items())
        if remote['draft']:
            run(['release','edit',args.tag,'--repo',args.repo,'--draft=false'])
        published = api(endpoint)
        assert not published['draft']
        state.update(state='published', completed_unix=time.time(),
                     total_asset_bytes=sum(info['size'] for info in expected.values()),
                     server_digest_count=sum(bool(indexed[n].get('digest')) for n in expected))
        save()
        print('RELEASE_PUBLISHED', published['html_url'], len(expected), flush=True)
    except Exception as exc:
        with lock:
            state.update(state='failed', error=str(exc))
            save()
        raise


if __name__ == '__main__':
    main()
