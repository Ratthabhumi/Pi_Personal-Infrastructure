# Owner clean-storage decision — 5 November 2026

AUTHORIZATION: the latest direct owner message explicitly authorizes deletion and fresh ext4 formatting of ONLY the previously identified approximately 1 TB ext4 partition, resolved by its approved old UUID. It supersedes the attached older "do not format/use SSD" plan and the earlier legacy-restore investigation. This authorization is not authority to repartition the disk, touch system/installer disks, expand LVM, change SSH/Tailscale identity, copy old secrets or deploy ACASH trading/data.

Approved post-format layout: label HOMELAB_DATA, new UUID at /data, /data/docker, /data/backups, /data/acash and /data/logs. Old applications, backups and secrets on the target are intentionally discarded; this is a fresh filesystem, not secure erasure. Data loss has no rollback. Existing OS/SSH/Tailscale and Windows development remain preserved.

Privileged execution requires the owner entering sudo authentication locally. Do not collect/store passwords or enable passwordless sudo. The owner has already approved deletion; do not ask for another deletion confirmation. Codex prepares/verifies the bounded packet and stops at that actual privilege boundary. The private original UUID is supplied in the host-only packet, not public Git.

Minimal foundation/monitoring is authorized after storage acceptance: official signed Ubuntu/Docker package sources, Docker/Compose/Ansible and one bounded loopback-only Node Exporter. No historical full-stack restore or automatic updates. /data/acash is empty, root-only reserved space; private data/jobs/brokers/trading remain unauthorized. NO_REAL_ORDERS and zero capital authority remain unchanged.
