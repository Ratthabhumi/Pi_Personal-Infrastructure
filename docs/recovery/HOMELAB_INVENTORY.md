Current observation — 5 November 2026: authorized format and /data acceptance passed; Docker/Compose/Ansible are installed, monitoring host HTTP failed. Do not run the clean/restore packets again. Use the service-only finish action in OWNER_DECISION_PACKET.md. Earlier snapshots below are historical.

Current decision update — 5 November 2026: owner explicitly approved clean formatting of the old-UUID-bound 1 TB partition and new /data storage. Legacy restoration/inspection instructions are superseded. Execution remains pending interactive sudo. See OWNER_CLEAN_STORAGE_DECISION_20261105.md and OWNER_DECISION_PACKET.md. Earlier host snapshots below remain evidence of their observation time.

# Inventory

FACT/EVIDENCE: [live sanitized snapshot](evidence/baseline-20261105.json), collected over authenticated SSH on 5 November 2026.

- Ubuntu 24.04.5 LTS; kernel 6.8.0-139-generic; x86_64; 4 logical CPUs (observed Intel i7-4510U).
- RAM 3,930,580 KiB; swap 3,930,108 KiB; available/free fields in snapshot.
- HDD: sda1, approximately 1 TB, ext4, unmounted. No contents inspected yet.
- Root device: sdb USB-attached approximately 500 GB; 100 GiB ext4 root LV. Reported ROTA=true, so SSD branding from historical baseline is not treated as independently proved.
- Installer media: sdc approximately 16 GB, excluded from any deployment operation.
- SSH/Tailscale and UFW systemd unit active/enabled. UFW effective policy requires root verification; unit state is not policy proof.
- Docker, Ansible, Fail2Ban absent. Unattended-upgrades already active before this task; agent did not enable/change it.
- No /data, /data/docker, /data/docker/.env, /ssd-data, /var/lib/docker, or recognized project checkout found in bounded home/projects/repos/apps search. This is not an exhaustive disk search.
- AC mains online, battery 100%/Not charging at the supplemental snapshot. No explicit lid policy found; effective closed-lid/restart survival NOT TESTED.

BLOCKER: LVM free extents, effective sshd/firewall configuration and old HDD data require privileged inspection. Host-private addresses/UUID/secrets are excluded from public evidence.
