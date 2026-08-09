# Platform Engineering & AI Infrastructure: Agile Sprint Roadmap

This document defines our evolutionary execution plan to transform an entry-level home setup into an enterprise-grade AI Cloud infrastructure using progressive Platform Engineering sprints.

---

## 🧭 Architectural Dependency Flow (Why Order Matters)
In modern Site Reliability Engineering (SRE), deploying application containers before automating the operating system and networking ingress leads to unmanageable Technical Debt. We follow a strict foundational execution pipeline:

```
[ Sprint 1: OS Automation & Hardening (Ansible) ]
                     │
                     ▼
[ Sprint 2: Edge Gateway & Zero-Trust Routing (Traefik + Tailscale DNS) ]
                     │
                     ▼
[ Sprint 3: Full Observability Telemetry & Logging (Prometheus + Grafana + Loki) ]
                     │
                     ▼
[ Sprint 4: SRE Autonomous Agents & Self-Documenting Scripts (Python + AI) ]
                     │
                     ▼
[ Sprint 5: Distributed AI Inference Engine (60k THB Build + GPU Mesh) ]
```

---

## 🏃 Sprint Breakdown Table

| Sprint | Phase & Objective | Target Deliveries | Core Technology | Duration | Status |
| :---: | :--- | :--- | :--- | :---: | :---: |
| **01** | **Infrastructure as Code Backbone**<br>Eliminate manual SSH setups; automate server OS bootstrapping, kernel optimizations, and Docker Engine provisioning. | • `00_bootstrap_server.yml`<br>• SSH hardened (Fail2ban/UFW)<br>• Kernel tuned for 24/7 reliability<br>• Docker Engine & Tailscale daemon config | **Ansible**<br>**Ubuntu 24.04**<br>**Make** | 1-2 Days | 🏆 **COMPLETED** |
| **02** | **Edge Routing & Secure Ingress**<br>Eliminate memorized port numbers (8080/3000) and establish HTTPS wildcard certificates over internal Tailscale mesh. | • Traefik Reverse Proxy<br>• Tailscale MagicDNS binding<br>• Portainer/Dockge Container Management UI<br>• Secure Domain routing (e.g. `*.homelab.ts.net`) | **Docker Compose**<br>**Traefik v3**<br>**Tailscale DNS** | 1-2 Days | 🏆 **COMPLETED** |
| **03** | **SRE Observability & Telemetry**<br>Implement Observability Driven Development (ODD). Ensure all metrics and logs are centralized before deploying application payloads. | • Prometheus / VictoriaMetrics Engine<br>• Grafana Live Dashboards<br>• Grafana Loki centralized system logging<br>• Uptime Kuma alerts to Telegram/Discord | **Prometheus**<br>**Grafana Loki**<br>**Alertmanager** | 2-3 Days | 🏆 **COMPLETED** |
| **04** | **Autonomous Operations & AI Bots**<br>Build automated resiliency tools and scripts that self-monitor, backup infrastructure, and write docs automatically. | • Restic automated volume snapshots<br>• Python script to scan live containers and commit Markdown table updates directly to Git<br>• Automated Docker image updates via Watchtower / Renovate | **Python SDK**<br>**Restic**<br>**GitHub Actions / Git** | 3-5 Days | 🏆 **COMPLETED** |
| **05** | **Production Infrastructure Refactoring**<br>Migrate to enterprise-grade layout. Move data to HDD, unify Compose files, drop kernel capabilities, and enforce tight security profiles. | • Unified `compose.yaml`<br>• Data migration to `/data/docker`<br>• Enforce security profiles | **DevOps Best Practices**<br>**Storage / ext4** | 1-2 Days | 🏆 **COMPLETED** |
| **06** | **Self-Hosted Apps & Advanced Monitoring**<br>Vaultwarden, AdGuard Home, Prometheus, VictoriaMetrics, Grafana, Alerting | • Vaultwarden Password Manager<br>• Advanced Alerting (Telegram/Discord) | **Self-Hosting**<br>**Alertmanager** | 2-3 Days | 🏆 **COMPLETED** |
| **07** | **Infrastructure as Code (IaC)**<br>Codify the entire Homelab infrastructure using Ansible and Terraform. | • Ansible playbooks for OS<br>• Terraform for Cloudflare DNS | **Ansible**<br>**Terraform** | Future Build | ⚪ *Planned* |
| **08** | **Continuous Integration / Deployment (CI/CD)**<br>Automate testing and deployment pipelines using GitHub Actions. | • GitHub Actions pipeline<br>• automated testing & linting | **GitHub Actions**<br>**CI/CD** | Future Build | ⚪ *Planned* |
| **09** | **Kubernetes Production Homelab**<br>Migrate Docker Compose workloads to a lightweight Kubernetes cluster (K3s) with GitOps. | • K3s Cluster Setup<br>• ArgoCD for GitOps | **K3s / Kubernetes**<br>**ArgoCD** | Future Build | ⚪ *Planned* |
---

## 📌 Sprint 1 & 2 Definition of Done (DoD)
Before closing Sprint 1 and moving to Sprint 2, the following conditions must be validated:
- [x] Autonomous GitOps execution (`make apply-local`) reconciles OS package states without manual configuration.
- [x] Ubuntu Firewall (UFW) active, blocking all external unsolicited ports while trusting Tailscale interface (`tailscale0`).
- [x] Docker Engine running natively and verified with non-root user permissions (`docker ps` works without `sudo`).
- [x] Server log rotation (`/etc/docker/daemon.json`) and automatic unattended OS patch installation verified.

### 🏁 Sprint 2 Definition of Done
- [x] Core routing stack (`docker/core/docker-compose.yml`) deploying Traefik v3 and Portainer CE successfully.
- [x] Portainer visual dashboard accessible directly via local browser without port conflicts.
- [x] Traefik container routing rules active across local Docker socket (`homelab_mesh` network bridge functional).

### 🏆 Sprint 3 Definition of Done (Completed)
- [x] Deploy VictoriaMetrics (low-RAM Prometheus alternative), Node Exporter, and cAdvisor.
- [x] Launch Grafana visualization dashboard accessible via browser (`http://homelab:3000` or Tailscale IP).
- [x] Establish live telemetry monitoring CPU, RAM, disk space, and container health.

### 🏆 Sprint 4 Definition of Done (Completed)
- [x] Deploy automated Docker container patching system (Watchtower) for unattended weekly updates.
- [x] Create Python self-documenting script (`autodox.py`) that audits running containers and updates markdown status tables.
- [x] Establish automated backup scripts with Restic/Tar to snapshot critical configs and volume payloads.

### 🏆 Sprint 5 Definition of Done (Completed)
- [x] Migrate all persistent Docker volume data to the `/data` HDD mount point.
- [x] Consolidate fragmented `docker-compose.yml` files into a single monolithic `/data/docker/compose.yaml`.
- [x] Harden security by applying `no-new-privileges:true` and read-only mounts where applicable.
- [x] Automatically mount HDD on boot using fstab UUIDs.

### 🏆 Sprint 6 Definition of Done (Completed)
- [x] Deploy AdGuard Home as a network-wide DNS sinkhole and ad blocker.
- [x] Deploy Vaultwarden for self-hosted secure password management via Tailscale HTTPS.
- [x] Deploy Uptime Kuma for internal service monitoring and external heartbeat tracking.
- [x] Integrate Telegram Bot API for real-time push notifications on service degradation.
- [x] Integrate Healthchecks.io for external server offline detection (Push method).
