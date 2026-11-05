Current observation - 5 November 2026 (live host audit): storage acceptance PASS, Docker data-root PASS, Node Exporter loopback HTTP 200 PASS, SSH/Tailscale/Docker PASS. The earlier monitoring failure is closed; use the 24/7 host hardening action in OWNER_DECISION_PACKET.md. Earlier snapshots below are historical.

# Inventory

FACT/EVIDENCE: [live sanitized snapshot](evidence/baseline-20261105.json), collected over authenticated SSH on 5 November 2026.

- Ubuntu 24.04.5 LTS; kernel 6.8.0-139-generic; x86_64; 4 logical CPUs (observed Intel i7-4510U).
- RAM 3,930,580 KiB; swap 3,930,108 KiB; available/free fields in snapshot.
Current live state (5 November 2026, read-only SSH audit, [evidence](evidence/host-audit-20261105.json)):

- HDD: sda1, 931.5 GB, ext4, mounted at `/data` with 870 GB free. Contains only `acash`, `backups`, `docker`, `logs` and `lost+found`.
- Root device: sdb USB-attached approximately 500 GB; 100 GiB ext4 root LV. Reported ROTA=true, so SSD branding is not independently proved.
- Installer media: sdc approximately 16 GB, excluded from any deployment operation.
- SSH, Tailscale and Docker: active and enabled. Docker CE 29.9.3 with data-root `/data/docker/engine`.
- Node Exporter: loopback `127.0.0.1:9100`, HTTP 200, non-root.
- UFW: installed but `ENABLED=no`; effective policy is currently no firewall. Owner action pending.
- Docker, Compose v2 and Ansible installed. `mew` is not in the `docker` group.
- AC mains online; logind has no overrides, so lid close would suspend. Closed-lid/restart survival NOT TESTED.

BLOCKER: effective firewall policy, closed-lid survival and reboot recovery require the owner-root action and a physical-access reboot. Host-private addresses/UUID/secrets are excluded from public evidence.
