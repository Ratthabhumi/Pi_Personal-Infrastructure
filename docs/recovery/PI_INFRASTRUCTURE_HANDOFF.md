Current observation — 5 November 2026: authorized format and /data acceptance passed; Docker/Compose/Ansible are installed, monitoring host HTTP failed. Do not run the clean/restore packets again. Use the service-only finish action in OWNER_DECISION_PACKET.md. Earlier snapshots below are historical.

# Pi clean-infrastructure handoff

Current scope is fresh HDD storage plus minimal foundation, not legacy restore. Latest explicit owner clean-storage decision supersedes the old no-format/use-root attachment. Existing source safeguards from Draft PR #1 remain: no push-triggered self-hosted deploy/LVM extension, broad chown/delete/password reset, blind pull/orphan removal or automatic full stack.

New controlled owner-only entry: scripts/recovery/clean_storage.py plus provision_foundation.sh. It is never executed by CI/Ansible by default. Live gates bind one old UUID to a single unmounted approximately 1 TB ext4 partition. New UUID backs /data; Docker data-root and startup depend on that exact mount. Foundation uses official signed sources; no root group privileges granted to the user. Standalone docker/compose.minimal.yaml runs only bounded loopback Node Exporter without the historical .env or stack. The old gated Ansible telemetry restore is retained for historical review, not called by clean setup.

Status: PREPARED, not executed with sudo. The owner checkout remains on its original feature branch; recovery branch remains isolated, Draft/unmerged. Use current PR HEAD/CI, not stale source status, as validation evidence. Actual storage/versions/container health are pending the owner result. No reboot or live Exit Node client test is claimed.

Next session reads the private clean result and exports only sanitized statuses/versions/digests. If partially failed, do not reformat or clear the attempt marker; repair the exact remaining phase. Confirm new UUID/mount/data-root/drop-in/HTTP metrics/resource limits, new Windows SSH session, Tailscale forwarding and actual external client egress. Backups and private secrets are new scoped work, never copied from old data.
