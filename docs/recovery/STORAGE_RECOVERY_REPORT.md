# Clean storage status — revised owner decision

FACT: the owner now authorizes intentional destruction of old data on the single old-UUID-bound approximately 1 TB ext4 partition. Legacy recovery is cancelled. This supersedes the earlier EXISTING_DATA_UNVERIFIED inspection plan; neither old-data classification nor backup recovery is required before the authorized format.

Current evidence: old identity matched, approximately 1 TB partition unmounted, system/installer disks separate; live privileged gates must repeat immediately before format. Formatting NOT EXECUTED; new UUID NOT AVAILABLE; /data mount NOT EXECUTED; persistence validation NOT EXECUTED; directory readiness NOT EXECUTED. No data has been deleted in this Codex session.

Prepared sequence: resolve/uniquely probe old UUID; inspect full block tree, holders and process mount namespaces; reject conflicts; persist one-attempt marker; format only that partition; label HOMELAB_DATA; capture new UUID; preserve fstab backup; atomically add the exact new UUID; verify/mount /data; create root-only docker/backups/acash (0700), logs (0750); synthetic I/O cleanup. No repartition, LVM expansion or writes to system/installer media. The physical disk partition table is preserved.

Docker's data-root is /data/docker/engine with RequiresMountsFor and exact UUID ExecStartPre. An absent/wrong mount must stop Docker, never silently store engine data on root. /data/acash remains empty and root-only. New services receive fresh private secrets only when individually approved; old .env/app files are never copied back.

Formatting is not secure erasure and is irreversible for this workflow. An old fstab backup does not restore the deleted filesystem or data; do not restore it blindly after format. Failed phases require state-aware repair without another mkfs. The new UUID and detailed commands are recorded in the owner's private result; redact UUID/device/IP metadata before publishing sanitized evidence. Same-disk backups are workspace only, not independent protection.
