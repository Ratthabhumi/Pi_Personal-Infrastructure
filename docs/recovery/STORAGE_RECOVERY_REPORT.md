# Storage recovery

Classification **EXISTING_DATA_UNVERIFIED**. FACT: live lsblk identifies the expected approximately 1 TB ext4 HDD as unmounted. Root has sufficient current headroom; no workload requirement justifies expanding LVM. No format, fsck repair, permanent mount/fstab change, ownership change or data deletion occurred.

PROPOSAL: the staged owner-root inspector resolves the explicitly approved UUID, verifies ext4 and approximately 1 TB size, rejects an already mounted filesystem, and mounts to a unique temporary /run location with ro,noload,nodev,nosuid,noexec. It reads only metadata/allowlisted layout presence, never secret/application contents, then unmounts and removes only its newly created empty mountpoint. It records cleanup failure for owner recovery. It never installs packages or creates /data.

Metadata readability alone does not establish database consistency, backup validity or application recoverability. EMPTY_FILESYSTEM_CONFIRMED is limited to an empty inspected filesystem namespace including lost+found, not free-space forensic erasure. Symlinks are not followed into live paths.

BLOCKER: owner sudo execution pending. After evidence, identify old data layout, verify backups/consistency and obtain the exact permanent mount/config restoration decision. Do not overwrite unknown historical data. Keep free LVM extents unallocated. Rollback for inspection: normal unmount only; if cleanup fails, inspect reported mount state before manual action. Never force unmount or delete a mounted directory.
