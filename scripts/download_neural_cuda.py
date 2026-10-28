"""Resumable Windows/Python 3.12 CUDA wheel download from the official index.

Use only if pip's large-file download stalls. The final SHA-256 is pinned to
the published PyTorch cu128 index. No package is executed or installed here.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path
from threading import Lock
from urllib.request import Request, urlopen

URL = 'https://download-r2.pytorch.org/whl/cu128/torch-2.7.1%2Bcu128-cp312-cp312-win_amd64.whl'
SHA = '2bb8c05d48ba815b316879a18195d53a6472a03e297d971e916753f8e1053d30'
SIZE = 3273024349
CHUNK = 16*1024*1024
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT/'data/vendor/neural-training/torch-2.7.1+cu128-cp312-cp312-win_amd64.whl'


def digest(path):
    h = sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()


def main():
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.exists() and TARGET.stat().st_size == SIZE and digest(TARGET) == SHA:
        print('Verified wheel already present.', flush=True)
        return
    partial = TARGET.with_suffix('.partial')
    state = TARGET.with_suffix('.parts.json')
    completed = set(json.loads(state.read_text())) if state.exists() and partial.exists() else set()
    if not partial.exists():
        with partial.open('wb') as f: f.truncate(SIZE)
    lock = Lock()
    total = (SIZE+CHUNK-1)//CHUNK

    def fetch(index):
        start = index*CHUNK; end = min(SIZE, start+CHUNK)-1
        request = Request(URL+f'?team17_chunk={index}', headers={'Range': f'bytes={start}-{end}'})
        for attempt in range(3):
            try:
                with urlopen(request, timeout=90) as response:
                    if response.status != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{SIZE}':
                        raise ValueError('Range response mismatch.')
                    payload = response.read(end-start+2)
                if len(payload) != end-start+1: raise ValueError('Incomplete chunk.')
                with partial.open('r+b') as f:
                    f.seek(start); f.write(payload)
                with lock:
                    completed.add(index)
                    state.write_text(json.dumps(sorted(completed)))
                    if len(completed) % 10 == 0 or len(completed) == total:
                        print(f'CUDA wheel chunks {len(completed)}/{total}', flush=True)
                return
            except Exception:
                if attempt == 2: raise
    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs = [executor.submit(fetch, i) for i in range(total) if i not in completed]
        for job in as_completed(jobs): job.result()
    if digest(partial) != SHA: raise ValueError('Final official-wheel checksum mismatch.')
    partial.replace(TARGET)
    print(f'Verified CUDA wheel: {TARGET}', flush=True)


if __name__ == '__main__': main()
