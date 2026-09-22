# Backup and restore

## What a backup contains
`backups\alice-YYYYmmdd-HHMMSS\`:
- `sqlite\alice.db`, `sqlite\tables.db` — taken with SQLite's **online backup API** (consistent while running).
- `qdrant\<snapshot>` — collection snapshot created through Qdrant's API, downloaded, then removed from Qdrant.
- `data\raw\`, `data\processed\` — original uploads and extracted text.
- `manifest.json` — creation time, version, schema version, sha256 of every file, row counts.

Retention: newest 7 backups. Backups contain private documents: they are gitignored and must not be placed in cloud-synced folders.

## Restore (verified procedure)
```powershell
.\scripts\windows\Restore-Alice.ps1 -Backup .\backups\alice-20260922-151344 -Destination C:\Temp\alice-restore
```
It refuses destinations inside live `storage\`/`data\`, verifies every sha256, copies to the new folder, runs
`PRAGMA integrity_check`, compares row counts with the manifest, and restores the Qdrant snapshot into a **temporary
collection**, checks its point count equals the number of chunks, then drops it. Live data is never overwritten.

To actually switch to a restored copy: `Stop-Alice.ps1`, move the current `storage\` and `data\` aside (do not delete),
copy the restored `sqlite\*.db` into `storage\sqlite\` and `data\*` into `data\`, upload the Qdrant snapshot to `alice_chunks`
(`POST /collections/alice_chunks/snapshots/upload`), `Start-Alice.ps1`.

## Tested
2026-09-22: backup of 11 files (4 documents, 7 chunks, 41 requests, 2 ledger rows) → restore into `%TEMP%` →
checksums 11/11, integrity ok, row counts equal, Qdrant snapshot restored to a temporary collection with 7 points; refusal
test against `storage\x` → REFUSED.
