"""Check the shipped file set and run offline validation. Hashes are not signatures."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def main():
    manifest=json.loads((ROOT/"MANIFEST.json").read_text(encoding="utf-8"))
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and p.name!="MANIFEST.json" and "__pycache__" not in p.parts and ".git" not in p.parts}
    if actual!=set(manifest):raise ValueError("manifest file set mismatch")
    for name,digest in manifest.items():
        path=PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:raise ValueError("unsafe path")
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError("hash mismatch: "+name)
    proc=subprocess.run([sys.executable,"-B","-m","unittest","-v","test_checker"],cwd=ROOT,timeout=60)
    if proc.returncode:return proc.returncode
    print(json.dumps({"status":"PASS_OFFLINE_REPLAY","manifest_files":len(manifest),"signature_verified":False,"lean_recompiled":False}))
    return 0


if __name__=="__main__":
    try:raise SystemExit(main())
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status":"REJECTED","reason":str(exc)}));raise SystemExit(1)
