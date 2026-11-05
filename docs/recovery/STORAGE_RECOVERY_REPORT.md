# Storage acceptance — actual owner execution

PASS: explicit old-filesystem safety gates; one authorized format; label/new UUID captured; new UUID matches live /data ext4 rw; synthetic write/read/delete; fstab static validation; root-only docker/backups/acash directories and logs 0750. Detailed UUID/command records remain private. Original result is preserved in the owner's state directory; sanitized evidence is monitoring-failure-20261105.json.

The original HDD data is now intentionally gone. Formatting is not secure erasure. Do not run the clean packet or remove its root attempt marker. Existing system/boot/LVM and installer media were excluded by the formatter's actual safety gates; no repartition or LVM expansion was executed.

Docker engine state was configured under /data/docker/engine with an exact UUID mount dependency. The finish helper verifies that live binding and fstab before touching the monitoring container. It contains no storage formatter/mount/fstab/package installation path. Actual reboot persistence is NOT TESTED; preserve remote recovery access.

/data/acash is reserved storage only; no financial workload or credential was deployed. /data/backups is a same-HDD workspace, not an independent/offsite backup. Do not restore old application state or secrets. Monitoring failure does not justify any repeated formatting.
