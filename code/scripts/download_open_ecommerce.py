"""Download Open e-commerce 1.0 (doi:10.7910/DVN/YGLYDY) from Harvard Dataverse.

Resumable (HTTP Range), retry with exponential backoff, md5 verification.
Usage: python download_open_ecommerce.py [outdir]
"""
import hashlib, json, sys, time, urllib.request
from pathlib import Path

DOI = "doi:10.7910/DVN/YGLYDY"
BASE = "https://dataverse.harvard.edu"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/repo-intro/build/input/public/open_ecommerce")
OUT.mkdir(parents=True, exist_ok=True)


UA = {"User-Agent": "Mozilla/5.0 (research download script)"}


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch(fid, path, size, tries=12, orig=False):
    for k in range(tries):
        have = path.stat().st_size if path.exists() else 0
        if have >= size:
            return
        try:
            req = urllib.request.Request(f"{BASE}/api/access/datafile/{fid}" + ("?format=original" if orig else ""), headers=UA)
            if have:
                req.add_header("Range", f"bytes={have}-")
            with urllib.request.urlopen(req, timeout=60) as r, open(path, "ab" if have else "wb") as f:
                if have and r.status != 206:  # server ignored Range: restart
                    f.truncate(0)
                while b := r.read(1 << 20):
                    f.write(b)
        except Exception as e:
            wait = min(2 ** k, 120)
            print(f"  retry {k+1}/{tries} after {e!r}; sleeping {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"failed: {path}")


meta = json.load(urllib.request.urlopen(urllib.request.Request(f"{BASE}/api/datasets/:persistentId/?persistentId={DOI}", headers=UA)))
for f in meta["data"]["latestVersion"]["files"]:
    d = f["dataFile"]; p = OUT / d["filename"]
    # ingested tabular files: fetch the original upload (listed md5/size refer to it)
    orig = bool(d.get("originalFileSize"))
    size = d["originalFileSize"] if orig else d["filesize"]
    print(d["filename"], size, flush=True)
    for attempt in range(3):
        fetch(d["id"], p, size, orig=orig)
        if md5(p) == d["md5"]:
            print("  ok md5", d["md5"], flush=True); break
        print("  md5 mismatch, redownloading", flush=True); p.unlink()
    else:
        raise RuntimeError(f"md5 failed {p}")
