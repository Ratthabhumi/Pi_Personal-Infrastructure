# Automation & Maintenance Scripts

This module contains autonomous utility scripts designed to keep infrastructure resilient without requiring manual admin interventions.

## Backup & Recovery Infrastructure

### 1. `auto_backup.sh` (Local Archive Engine)
- **Current Implementation:** Plain `tar.gz` archive of `/data/docker` written to `/data/backups` with SHA-256 integrity checksum generation and flock concurrency protection.
- **Status:** IMPLEMENTED IN REPOSITORY / REQUIRES REAL-HOMELAB SYSTEMD TIMER ACTIVATION.
- **Storage Risk (R4):** `/data/docker` and `/data/backups` reside on the **same physical storage device**. Local backup protects against accidental file deletion or bad deployments, but **does NOT constitute disaster recovery**.
- **Evidence Retention (O3):** Configured to preserve active observation-window evidence plus the O3 seven-day margin.
- **Off-Host / Disaster Recovery (Sprint 15):** Encrypted incremental offsite backups (e.g. via Restic/Borg to external/cloud object storage) remain **NOT IMPLEMENTED / PLANNED FOR SPRINT 15**.

### 2. Planned Automation Scripts
- **`doc_generator.py` (Live Markdown Autodoc)**: Python tool scanning running containers and generating architecture summaries into Git. (PLANNED)
- **`health_remediator.sh` (Self-Healing Watchdog)**: Automated container recovery watchdog. (PLANNED)
