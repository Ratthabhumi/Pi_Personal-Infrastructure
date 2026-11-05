# Pi infrastructure handoff

Source base: freshly fetched origin/main 3ce27f09e742768633c23a5d0746a004bc3a1727. Existing owner checkout remains on feature/acash-shadow-tournament-deploy at 98c6c8521eb8710940f76a361f4f4a3ad0a029; no pull/reset/stash/switch there. Recovery changes are isolated on codex/homelab-recovery-20261105. Use the Draft PR head and checks as current implementation evidence.

Implemented source correction: ignore_errors removed from Docker key fetch; auto-deploy/LVM workflows neutralized; old full local bootstrap and Make deployment/rebuild routes fail closed; bootstrap needs explicit authority; restore requires exact approved mounted ext4 UUID/config digest/private secret-file metadata and explicit telemetry list. No automatic copy/chown/reset/delete or orphan removal. Existing images only, no dependency starts. Traefik insecure endpoint removed; Watchtower needs opt-in; password/token/secret interpolations fail when missing.

Host readiness: SSH works; package foundation, storage and application health remain incomplete. A .env must be supplied/recovered privately only after storage inspection; historical demo/default identity files are not an approved secrets contract. Do not execute any historical full-stack instructions from README. Docker group membership is root-equivalent and is not granted by this task.

Next: read privileged metadata result; review intended mounts/backups, resource budget and Docker/firewall interaction before provisioning; start only one bounded approved service at a time; validate health, limits, persistence, authentication, backup and reconnect. Full stack/Nextcloud/identity/ACASH restoration remains separately gated. No existing backup is claimed verified.
