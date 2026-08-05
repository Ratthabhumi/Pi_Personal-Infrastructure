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
| **02** | **Edge Routing & Secure Ingress**<br>Eliminate memorized port numbers (8080/3000) and establish HTTPS wildcard certificates over internal Tailscale mesh. | • Traefik Reverse Proxy<br>• Tailscale MagicDNS binding<br>• Portainer/Dockge Container Management UI<br>• Secure Domain routing (e.g. `*.homelab.ts.net`) | **Docker Compose**<br>**Traefik v3**<br>**Tailscale DNS** | 1-2 Days | 🟡 **IN PROGRESS** |
| **03** | **SRE Observability & Telemetry**<br>Implement Observability Driven Development (ODD). Ensure all metrics and logs are centralized before deploying application payloads. | • Prometheus / VictoriaMetrics Engine<br>• Grafana Live Dashboards<br>• Grafana Loki centralized system logging<br>• Uptime Kuma alerts to Telegram/Discord | **Prometheus**<br>**Grafana Loki**<br>**Alertmanager** | 2-3 Days | ⚪ *Planned* |
| **04** | **Autonomous Operations & AI Bots**<br>Build automated resiliency tools and scripts that self-monitor, backup infrastructure, and write docs automatically. | • Restic automated volume snapshots<br>• Python script to scan live containers and commit Markdown table updates directly to Git<br>• Automated Docker image updates via Watchtower / Renovate | **Python SDK**<br>**Restic**<br>**GitHub Actions / Git** | 3-5 Days | ⚪ *Planned* |
| **05** | **AI Inference & GPU Expansion**<br>Integrate future ~60,000 THB AI Server into cluster mesh. Enable local LLMs to act as private cloud co-workers. | • Proxmox VE / Linux AI stack deployment<br>• NVIDIA Container Toolkit configuration<br>• Ollama + Open WebUI (Local ChatGPT clone)<br>• RAG Vector Database integration | **NVIDIA CUDA**<br>**Ollama / vLLM**<br>**Milvus / ChromaDB** | Future Build | ⚪ *Planned* |

---

## 📌 Sprint 1 & 2 Definition of Done (DoD)
Before closing Sprint 1 and moving to Sprint 2, the following conditions must be validated:
- [x] Autonomous GitOps execution (`make apply-local`) reconciles OS package states without manual configuration.
- [x] Ubuntu Firewall (UFW) active, blocking all external unsolicited ports while trusting Tailscale interface (`tailscale0`).
- [x] Docker Engine running natively and verified with non-root user permissions (`docker ps` works without `sudo`).
- [x] Server log rotation (`/etc/docker/daemon.json`) and automatic unattended OS patch installation verified.

### 🏃 Sprint 2 Definition of Done (Active Targets)
- [ ] Core routing stack (`docker/core/docker-compose.yml`) deploying Traefik v3 and Portainer CE successfully.
- [ ] Portainer visual dashboard accessible directly via local browser without port conflicts.
- [ ] Traefik container routing rules active across local Docker socket (`homelab_mesh` network bridge functional).
