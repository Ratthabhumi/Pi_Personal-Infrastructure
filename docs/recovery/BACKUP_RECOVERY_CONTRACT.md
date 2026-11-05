# Backup and recovery contract (minimal)

Date: 5 November 2026. Status: **CONTRACT DEFINED / OFF-DEVICE TARGET MISSING**.

## What must be recoverable

| Asset | Where it lives | Recoverable without backup? |
|---|---|---|
| Host OS configuration (`/etc/fstab`, docker daemon.json, drop-ins, UFW, logind) | root filesystem | No — but reproducible from this repository + owner actions |
| Docker engine metadata and images | `/data/docker` | No — images can be re-pulled, metadata cannot |
| ACASH application data / warehouse | `/data/acash` | **No** — ACASH-owned |
| Container definitions | this repository | Yes, from Git |
| Secrets / provider credentials | ACASH-owned | Must be re-issued, never copied into Git |

## Minimum contract

1. **3-2-1 principle, minimum viable version:** one copy on `/data`, one copy off the device.
2. `/data/backups` is a same-HDD staging copy. A disk failure or `mkfs` destroys both source and copy. It is **not** a backup of record.
3. Off-device copy is **BLOCKED** until the owner nominates a destination (external USB kept disconnected, another machine, or an encrypted cloud bucket). No destination was created by this repository.
4. Target: host configuration snapshot daily; ACASH data snapshot at a cadence ACASH defines (EOD after its warehouse load is a sensible default).
5. Retention: 7 daily + 4 weekly for host config; ACASH retention is ACASH-owned.
6. Encryption: required for anything leaving the host. Keys must not be stored on the same host.
7. Restore test: at least once, on a scratch disk or VM, before relying on the backup. Restoring onto a formatted `/data` is a last resort, never a routine step.

## Host recovery order

1. Reinstall/repair Ubuntu on the system disk; do not format the installer media.
2. Recreate `/data` mount by UUID from this repository's documented fstab contract.
3. Restore `/etc/docker/daemon.json`, the `docker.service` drop-in and the logind/UFW drop-ins from the host config snapshot or this repository.
4. Start Docker, confirm `docker info` reports `data-root=/data/docker/engine`.
5. Restore ACASH-owned data using ACASH's own runbook, then start its containers.
6. Re-verify SSH, Tailscale, DNS, time sync and Node Exporter.

## Current gaps

- No off-device destination.
- No installed backup timer (`homelab-backup.timer` is `not-found`).
- No measured RPO/RTO.
- No restore rehearsal.
- `/data/acash` is empty, so there is currently nothing ACASH-owned to back up.
