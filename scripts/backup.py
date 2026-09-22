"""Consistent backup / verified restore for Alice.

backup                -> backups/alice-<ts>/ : SQLite via online backup API, Qdrant collection snapshot via API,
                         raw+processed files, manifest.json with sha256 of every file.
restore <dir> <dest>  -> validates checksums, restores SQLite + files into <dest> (never the live storage),
                         restores the Qdrant snapshot into a TEMPORARY collection, verifies counts, drops it.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from apps.api.config import ROOT, settings
from services.rag.qdrant import COLLECTION

KEEP = 7  # retention: newest N backups


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sqlite_backup(src: Path, dst: Path) -> None:
    s = sqlite3.connect(src)
    d = sqlite3.connect(dst)
    with d:
        s.backup(d)
    d.close()
    s.close()


def backup() -> Path:
    cfg = settings()
    out = ROOT / "backups" / f"alice-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    (out / "sqlite").mkdir(parents=True)
    for db in (cfg.ops_db, cfg.tables_db):
        if db.exists():
            sqlite_backup(db, out / "sqlite" / db.name)
    q = cfg.qdrant_url.rstrip("/")
    with httpx.Client(timeout=300) as c:
        if c.get(f"{q}/collections/{COLLECTION}").status_code == 200:
            snap = c.post(f"{q}/collections/{COLLECTION}/snapshots?wait=true").json()["result"]["name"]
            (out / "qdrant").mkdir()
            with c.stream("GET", f"{q}/collections/{COLLECTION}/snapshots/{snap}") as r, (out / "qdrant" / snap).open("wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)
            c.delete(f"{q}/collections/{COLLECTION}/snapshots/{snap}")  # keep only our copy
    for sub in ("raw", "processed"):
        src = cfg.data_dir / sub
        if src.exists():
            shutil.copytree(src, out / "data" / sub)
    files = {str(p.relative_to(out)).replace("\\", "/"): sha256(p) for p in sorted(out.rglob("*")) if p.is_file()}
    counts = {}
    con = sqlite3.connect(out / "sqlite" / cfg.ops_db.name)
    for t in ("documents", "chunks", "datasets", "facts", "requests", "ledger"):
        counts[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    con.close()
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "alice_version": "0.1.0-beta.1",
                "schema_version": 1, "files": files, "row_counts": counts, "qdrant_collection": COLLECTION}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    olds = sorted((ROOT / "backups").glob("alice-*"))[:-KEEP]
    for o in olds:
        shutil.rmtree(o, ignore_errors=True)
    print(f"backup OK: {out} ({len(files)} files, rows {counts})")
    return out


def restore(src: Path, dest: Path) -> None:
    cfg = settings()
    live = {cfg.storage_dir.resolve(), cfg.data_dir.resolve(), ROOT.resolve()}
    if dest.resolve() in live or any(p in dest.resolve().parents for p in (cfg.storage_dir.resolve(), cfg.data_dir.resolve())):
        sys.exit("REFUSED: restore destination overlaps live data. Use an explicit separate folder.")
    m = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    bad = [f for f, h in m["files"].items() if sha256(src / f) != h]
    if bad:
        sys.exit(f"REFUSED: checksum mismatch in {bad[:5]}")
    if dest.exists():
        sys.exit(f"REFUSED: {dest} already exists")
    shutil.copytree(src, dest)
    con = sqlite3.connect(dest / "sqlite" / cfg.ops_db.name)
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    for t, n in m["row_counts"].items():
        got = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        assert got == n, (t, got, n)
    con.close()
    snaps = list((dest / "qdrant").glob("*.snapshot")) if (dest / "qdrant").exists() else []
    qinfo = "no snapshot"
    if snaps:
        tmp = f"restore_test_{int(time.time())}"
        q = cfg.qdrant_url.rstrip("/")
        with httpx.Client(timeout=300) as c, snaps[0].open("rb") as f:
            r = c.post(f"{q}/collections/{tmp}/snapshots/upload?wait=true", files={"snapshot": (snaps[0].name, f)})
            r.raise_for_status()
            restored = c.get(f"{q}/collections/{tmp}").json()["result"]["points_count"]
            live_n = c.get(f"{q}/collections/{COLLECTION}").json()["result"]["points_count"]
            c.delete(f"{q}/collections/{tmp}")
        expected = m["row_counts"]["chunks"]
        assert restored == expected, (restored, expected)
        qinfo = f"qdrant snapshot restored into temporary collection: {restored} points (== {expected} chunks in backup; live now {live_n}); temp collection dropped"
    print(f"restore OK into {dest}: checksums {len(m['files'])}/{len(m['files'])}, sqlite integrity ok, row counts match; {qinfo}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["backup"]:
        backup()
    elif sys.argv[1:2] == ["restore"] and len(sys.argv) == 4:
        restore(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        sys.exit("usage: backup | restore <backup_dir> <new_dest_dir>")
