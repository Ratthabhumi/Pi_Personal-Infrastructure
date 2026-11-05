Current observation - 5 November 2026 (live host audit): storage acceptance PASS, Docker data-root PASS, Node Exporter loopback HTTP 200 PASS, SSH/Tailscale/Docker PASS. The earlier monitoring failure is closed; use the 24/7 host hardening action in OWNER_DECISION_PACKET.md. Earlier snapshots below are historical.

# Pi clean-infrastructure handoff

Current scope is fresh HDD storage plus minimal foundation, not legacy restore. Latest explicit owner clean-storage decision supersedes the old no-format/use-root attachment. Existing source safeguards from Draft PR #1 remain: no push-triggered self-hosted deploy/LVM extension, broad chown/delete/password reset, blind pull/orphan removal or automatic full stack.

New controlled owner-only entry: scripts/recovery/clean_storage.py plus provision_foundation.sh. It is never executed by CI/Ansible by default. Live gates bind one old UUID to a single unmounted approximately 1 TB ext4 partition. New UUID backs /data; Docker data-root and startup depend on that exact mount. Foundation uses official signed sources; no root group privileges granted to the user. Standalone docker/compose.minimal.yaml runs only bounded loopback Node Exporter without the historical .env or stack. The old gated Ansible telemetry restore is retained for historical review, not called by clean setup.

Status: storage and foundation EXECUTED and accepted. `/data` is mounted from the new UUID, Docker uses `/data/docker/engine`, and Node Exporter answers HTTP 200 on loopback. Recovery branch remains isolated, Draft/unmerged. Use current PR HEAD/CI plus [host-audit-20261105.json](evidence/host-audit-20261105.json) as evidence, not stale source badges.

Next: owner runs the 24/7 hardening action in OWNER_DECISION_PACKET.md (logind no-suspend + SSH-safe UFW), then reboots with physical access and confirms SSH/Tailscale/Docker/metrics and closed-lid survival. Off-device backup, live Exit Node client egress and independent uplink remain separate work. Never reformat or clear the attempt marker.
