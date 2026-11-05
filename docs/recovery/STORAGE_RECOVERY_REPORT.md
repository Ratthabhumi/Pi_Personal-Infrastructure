## Corrected v2 — actual preflight result

Owner sudo authentication DID succeed. The original invocation stopped at live-storage-safety-gates / PHYSICAL_PARENT_NOT_PROVEN with formatting=NOT_EXECUTED and no mkfs command in its report. Old filesystem remains visible; SSH/Tailscale active. Verified on the actual host: PATH-only lsblk JSON without --tree returns 9 flat entries; adding --tree returns 3 disk trees and the same physical-parent gate passes. This was a source bug, not evidence of a wrong disk or failed password.

Production snapshot now explicitly requests --tree. Seven Linux regressions pass, including an integration check of real lsblk parent edges. v2 uses a separate bundle/result while retaining original evidence and the same root one-attempt lock/marker; it never clears a marker. The corrected root action must still verify its absence and every safety gate before formatting. The local Windows command below is updated to v2. No actual format, new UUID, mount, packages or monitoring acceptance has occurred. The v2 owner packet prints sanitized result fields so a preflight failure is visible instead of only a closed connection. See evidence/clean-topology-fix-20261105.json.

# Clean storage status — revised owner decision

FACT: the owner now authorizes intentional destruction of old data on the single old-UUID-bound approximately 1 TB ext4 partition. Legacy recovery is cancelled. This supersedes the earlier EXISTING_DATA_UNVERIFIED inspection plan; neither old-data classification nor backup recovery is required before the authorized format.

Current evidence: old identity matched, approximately 1 TB partition unmounted, system/installer disks separate; live privileged gates must repeat immediately before format. Formatting NOT EXECUTED; new UUID NOT AVAILABLE; /data mount NOT EXECUTED; persistence validation NOT EXECUTED; directory readiness NOT EXECUTED. No data has been deleted in this Codex session.

Prepared sequence: resolve/uniquely probe old UUID; inspect full block tree, holders and process mount namespaces; reject conflicts; persist one-attempt marker; format only that partition; label HOMELAB_DATA; capture new UUID; preserve fstab backup; atomically add the exact new UUID; verify/mount /data; create root-only docker/backups/acash (0700), logs (0750); synthetic I/O cleanup. No repartition, LVM expansion or writes to system/installer media. The physical disk partition table is preserved.

Docker's data-root is /data/docker/engine with RequiresMountsFor and exact UUID ExecStartPre. An absent/wrong mount must stop Docker, never silently store engine data on root. /data/acash remains empty and root-only. New services receive fresh private secrets only when individually approved; old .env/app files are never copied back.

Formatting is not secure erasure and is irreversible for this workflow. An old fstab backup does not restore the deleted filesystem or data; do not restore it blindly after format. Failed phases require state-aware repair without another mkfs. The new UUID and detailed commands are recorded in the owner's private result; redact UUID/device/IP metadata before publishing sanitized evidence. Same-disk backups are workspace only, not independent protection.
