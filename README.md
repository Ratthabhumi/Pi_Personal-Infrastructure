# 🏛️ Enterprise HomeLab & AI Cloud Infrastructure Monorepo

![Architecture Mode: Production & GitOps](https://img.shields.io/badge/Architecture-GitOps%20%2F%20IaC-blue?style=for-the-badge)
![OS: Ubuntu Server 24.04 LTS](https://img.shields.io/badge/Ubuntu%20Server-24.04%20LTS-e95420?style=for-the-badge&logo=ubuntu)
![Networking: Tailscale Mesh](https://img.shields.io/badge/Networking-Tailscale%20Mesh-orange?style=for-the-badge)
![CI Status](https://img.shields.io/github/actions/workflow/status/Ratthabhumi/Pi_Personal-Infrastructure/ci.yml?label=CI%20Linting&style=for-the-badge)
![CD Status](https://img.shields.io/github/actions/workflow/status/Ratthabhumi/Pi_Personal-Infrastructure/cd.yml?label=CD%20Deploy&style=for-the-badge)
![Project Status: Sprint 13 (Nextcloud Private Cloud) Active](https://img.shields.io/badge/Project%20Status-Sprint%2013%20(Nextcloud%20Private%20Cloud)%20COMPLETED-success?style=for-the-badge)

---

## 📌 Vision & Philosophy
This repository serves as the **Single Source of Truth (SSOT)** for deploying, maintaining, monitoring, and scaling a personal cloud and Artificial Intelligence infrastructure on an **Acer Aspire V13 (`mew@homelab` / Ubuntu 24.04 LTS)**.

We strictly abide by modern **DevOps, Site Reliability Engineering (SRE), and Platform Engineering** practices:
1. **GitOps Single Source of Truth**: All infrastructure changes, deployment files (`compose.yaml`), and configurations are authored on the local workstation (VS Code), pushed to GitHub, and applied automatically via CI/CD or Ansible.
2. **Cattle, Not Pets**: Servers and configurations are completely modular, automated, and ephemeral. Rebuilding takes minutes via declarative code.
3. **Zero-Trust Security**: No assumptions are made regarding local networks; we enforce least-privilege, encrypted network overlays (Tailscale), UFW firewall, and isolated Docker network bridges.
4. **Observability Driven Development (ODD)**: Every running container, service, and database explicitly outputs telemetry, health checks, and active monitoring in Uptime Kuma.

---

## 🗺️ Sprint Execution & Progress Roadmap

### 🟢 PHASE 1: Foundations, Ingress & Observability (COMPLETED)

| Sprint | Objective | Deliverables | Key Technologies | Status |
| :---: | :--- | :--- | :--- | :---: |
| **01** | **IaC OS Bootstrap & Hardening** | OS automation, UFW Firewall, Fail2ban, Kernel tuning, Tailscale daemon | **Ansible**, **Ubuntu 24.04** | 🏆 **COMPLETED** |
| **02** | **Edge Routing & Secure Ingress** | Traefik v3 reverse proxy, Tailscale MagicDNS, Portainer CE container management | **Traefik v3**, **Portainer** | 🏆 **COMPLETED** |
| **03** | **SRE Observability & Telemetry** | VictoriaMetrics (low-RAM engine), Node Exporter (`pid: host`), cAdvisor, Grafana | **VictoriaMetrics**, **Grafana** | 🏆 **COMPLETED** |
| **04** | **Autonomous Operations & Backup** | Unattended container updates (Watchtower), automated daily backups, `autodox.py` | **Watchtower**, **Python**, **Bash** | 🏆 **COMPLETED** |
| **05** | **Production Storage Refactoring** | Monolithic `/data/docker/compose.yaml`, storage migration to HDD `/data`, LVM expansion | **Docker Compose**, **ext4/LVM** | 🏆 **COMPLETED** |
| **06** | **Self-Hosted Security & DNS Apps** | Vaultwarden (Tailscale HTTPS), AdGuard Home DNS sinkhole, Uptime Kuma alerting | **Vaultwarden**, **AdGuard**, **Kuma** | 🏆 **COMPLETED** |
| **07** | **Infrastructure as Code (IaC)** | Unified Ansible deployment playbooks (`01_deploy_homelab.yml`), Makefile automation | **Ansible**, **Make** | 🏆 **COMPLETED** |
| **08** | **Continuous Integration & CD** | GitHub Actions CI/CD workflows, native self-hosted runner on `mew@homelab` | **GitHub Actions**, **CI/CD** | 🏆 **COMPLETED** |
| **09** | **Homelab Dashboard Portal** | Homepage Dashboard (`gethomepage/homepage`), host vitals widgets, service catalog | **Homepage Dashboard** | 🏆 **COMPLETED** |

---

### 🟡 PHASE 2: Enterprise Cloud & DBaaS (IN PROGRESS)

| Sprint | Objective | Deliverables | Key Technologies | Status |
| :---: | :--- | :--- | :--- | :---: |
| **10** | **Database as a Service (DBaaS)** | Centralized PostgreSQL 16 server, pgAdmin 4 Auto-Provisioned Web UI, automated multi-tier daily backup dumps | **PostgreSQL 16**, **pgAdmin 4**, **Docker** | 🏆 **COMPLETED** |
| **11** | **In-Memory Cache & Queue** | Centralized Redis in-memory cache layer to speed up upcoming apps and background job workers | **Redis 7 Alpine** | 🏆 **COMPLETED** |
| **12** | **Single Sign-On (SSO) & IAM** | Centralized authentication, 2FA/FIDO2, Traefik ForwardAuth integration | **Authelia**, **PostgreSQL**, **Redis** | 🏆 **COMPLETED** |
| **13** | **Private Cloud Storage** | Self-hosted cloud storage with multi-tier storage layout (SATA SSD + 1TB HDD) and mobile sync (Nextcloud) | **Nextcloud**, **PostgreSQL**, **Redis** | 🏆 **COMPLETED** |
| **14** | **Self-Hosted Git Service** | Private lightweight Git repository for local projects or GitHub mirroring | **Gitea / Forgejo**, **Git** | ⚪ *Next Up* |
| **15** | **Disaster Recovery (Offsite)** | Encrypted offsite cloud backups to remote cloud storage via Rclone schedules | **Rclone**, **Restic** | ⚪ *Planned* |
| **16** | **Knowledge Management** | Centralized documentation, markdown notes, and personal wiki platform | **Wiki.js / Outline** | ⚪ *Planned* |
| **17** | **Advanced Log Aggregation** | Centralized logging engine and log shipper (no more manual `docker logs`) | **Grafana Loki**, **Promtail** | ⚪ *Planned* |
| **18** | **Smart Home Automation** | Localized IoT & smart device control center | **Home Assistant Core**, **MQTT** | ⚪ *Planned* |
| **19** | **Threat Defense & IPS** | Dynamic malicious IP blocking and Intrusion Prevention System | **CrowdSec**, **Traefik Bouncer** | ⚪ *Planned* |
| **20** | **Self-Hosted VPN Control Plane** | Sovereign Tailscale control server (Headscale) | **Headscale** | ⚪ *Planned* |

---

### 🟣 EXTRA SPRINT: Hardware Dependent
*Status: Awaiting Hardware Upgrade (Minimum 16GB RAM recommended).*

| Sprint | Objective | Deliverables | Key Technologies | Status |
| :---: | :--- | :--- | :--- | :---: |
| **21** | **Private AI Infrastructure** | Local Large Language Models (LLMs) for private, offline AI assistance | **Ollama**, **Open-WebUI** | ⏸️ *On Hold* |

---

## 🌐 Live Service & Web UI Matrix

| Service | Internal Web URL / Endpoint | Purpose | Credentials / Access |
| :--- | :--- | :--- | :--- |
| **Homepage** | `http://home.mew.lab` *(https)* | Central Homelab Dashboard Portal | Public Local / Tailscale |
| **Portainer CE** | `http://portainer.mew.lab` *(https)* | Docker Container Visual Management | 🛡️ **Guarded by Authelia SSO** |
| **Grafana** | `http://grafana.mew.lab` *(https)* | Metrics & Health Telemetry Visualization | `admin` / `admin123` |
| **VictoriaMetrics** | `http://vmetrics.mew.lab` | High-Performance Time-Series Database | Internal / Prometheus compatible |
| **Traefik** | `http://traefik.mew.lab` *(https)* | Edge Routing & Ingress Dashboard | 🛡️ **Guarded by Authelia SSO** |
| **AdGuard Home** | `http://adguard.mew.lab` *(https)* | Network DNS & Ad-Blocker | `admin` / `admin123` |
| **Vaultwarden** | `https://homelab.tail35e4b4.ts.net` | Zero-Trust Password Vault (Tailscale HTTPS) | Private Vault Login |
| **Uptime Kuma** | `http://kuma.mew.lab` *(https)* | Live Service Monitoring & Alerting | 🛡️ **Guarded by Authelia SSO** |
| **pgAdmin 4** | `http://pgadmin.mew.lab` *(https)* | Centralized PostgreSQL Web Administration | 🛡️ **Guarded by Authelia SSO** |
| **Nextcloud** | `http://cloud.mew.lab` *(https)* | Private Cloud Storage, Photos & WebDAV | `admin` / `admin123` |
| **PostgreSQL** | `postgres:5432` *(Internal Network)* | Relational Database Engine (DBaaS) | `admin` / `admin123` (`homelab` db) |
| **Redis Cache** | `redis:6379` *(Internal Network)* | In-Memory Cache & Message Queue Layer | `admin123` |
| **Authelia SSO** | `http://auth.mew.lab` *(https)* | Centralized Single Sign-On & 2FA Gateway | `admin` หรือ `mew` / `admin123` |

---

## 📂 Repository Directory Structure

```
homelab/
├── .github/                      # [CI/CD Layer] GitHub Actions for Linting (CI) & Deployment (CD)
├── ansible/                      # [OS / Provisioning Layer] Automation playbooks & host definitions
│   ├── inventory/                # Target machines list (homelab server & future AI desktop)
│   └── playbooks/                # Step-by-step OS harding, package & docker installers
├── terraform/                    # [External Infrastructure] Cloudflare DNS Management (Template)
├── docker/                       # [Compute / Container Layer] Monolithic Compose Configuration
│   ├── compose.yaml              # Unified declarative stack (Traefik, DBaaS, Observability, Vaultwarden, AdGuard)
│   ├── pgadmin/config/           # Auto-provisioning declarative database definitions (servers.json)
│   ├── homepage/config/          # Homepage dashboard layout & service catalog
│   └── prometheus/config/        # Prometheus metric scrape configs for VictoriaMetrics
├── kubernetes/                   # [Orchestration Layer] Future declarative K3s / GitOps Helm deployment
├── scripts/                      # Utility scripts (Automated Restic backups, Self-healing, Document bots)
├── docs/                         # Architecture designs, runbooks, post-mortems, and sprint roadmaps
│   ├── architecture/             # High-level system, storage, and networking diagrams
│   └── runbooks/                 # Step-by-step operating & crisis resolution procedures
├── Makefile                      # Developer Ergonomics: Unified commands (make apply-local, etc.)
└── .gitignore                    # Iron-clad credential & state file exclusions
```

---

## 🚀 Developer Ergonomics & GitOps Workflow

### 1. Workstation (Local VS Code):
```powershell
# Commit changes and trigger automated deployment
git add .
git commit -m "feat(service): add new capability"
git push origin main
```

### 2. Homelab Server (`mew@homelab`):
```bash
# Pull changes and apply via automated Ansible reconcile
cd ~/Pi_Personal-Infrastructure
git pull origin main
make apply-local
```

---

## 🔒 Security & Secrets Management Architecture

To maintain strict security on a **Public Repository** while providing continuous GitOps deployment:
1. **Secret Decoupling:** All plain-text passwords and fallback strings (`:-admin123`, `:-a_very_secure_...`) are removed from Git-tracked manifests (`compose.yaml`, `configuration.yml`, `.env.example`).
2. **Server Secret Contract:** The single source of truth for runtime secrets is `/data/docker/.env` residing exclusively on the host server (`mew@homelab`), strictly excluded from Git.
3. **Container Ingestion:** Docker Compose injects credentials via standard environment variables (`AUTHELIA_STORAGE_POSTGRES_PASSWORD`, `REDIS_PASSWORD`, etc.), preventing credential leaks during deployment.

---

## 🔒 Security & Secrets Warning
**NEVER** commit plain-text passwords, SSH private keys, tokens, or `.env` files directly into this repository. All confidential parameters rely on local `/data/docker/.env` on the host and strictly excluded Git ignore templates.

