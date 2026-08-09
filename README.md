# Enterprise HomeLab & AI Cloud Infrastructure Monorepo

![Architecture Mode: Production & GitOps](https://img.shields.io/badge/Architecture-GitOps%20%2F%20IaC-blue?style=for-the-badge)
![OS: Ubuntu Server 24.04 LTS](https://img.shields.io/badge/Ubuntu%20Server-24.04%20LTS-e95420?style=for-the-badge&logo=ubuntu)
![Networking: Tailscale Mesh](https://img.shields.io/badge/Networking-Tailscale%20Mesh-orange?style=for-the-badge)

## 📌 Vision & Philosophy
This repository serves as the **Single Source of Truth (SSOT)** for deploying, maintaining, monitoring, and scaling a personal cloud and Artificial Intelligence infrastructure.

We strictly abide by modern **DevOps, Site Reliability Engineering (SRE), and Platform Engineering** practices:
1. **Cattle, Not Pets**: Servers and configurations are completely modular, automated, and ephemeral. Should any compute instance fail, rebuilding it takes minutes via code.
2. **Zero-Trust Security**: No assumptions are made regarding local area networks; we enforce least-privilege, encrypted network overlays (Tailscale), and robust secrets management.
3. **Observability Driven Development (ODD)**: Every running container, service, and automation workflow explicitly outputs diagnostics, logs, and telemetry.
4. **Autonomous Agent Ready**: Structured clean to enable LLM agents to monitor, debug, self-heal, and dynamically document infrastructure states.

---

## 📂 Repository Directory Structure

```
homelab/
├── .github/                      # CI/CD Workflows, GitHub Actions, Automated linters & Security bots
├── ansible/                      # [OS / Provisioning Layer] Automation playbooks & host definitions
│   ├── inventory/                # Target machines list (homelab server & future AI desktop)
│   └── playbooks/                # Step-by-step OS harding, package & docker installers
├── terraform/                    # [External Infrastructure] Cloudflare DNS Management (Template)
├── docker/                       # [Compute / Container Layer] Monolithic Compose Configuration
│   ├── compose.yaml              # Unified declarative stack (Traefik, Observability, Vaultwarden, AdGuard, Kuma)
│   └── ai-platform/              # (Future) Local LLMs, Vector DBs, Worker nodes & Inference engines
├── kubernetes/                   # [Orchestration Layer] Future declarative K3s / GitOps Helm deployment
├── scripts/                      # Utility scripts (Automated Restic backups, Self-healing, Document bots)
├── docs/                         # Architecture designs, runbooks, post-mortems, and DR plans
│   ├── architecture/             # High-level system & networking diagrams
│   └── runbooks/                 # Step-by-step operating & crisis resolution procedures
├── Makefile                      # Developer Ergonomics: Unified commands (make bootstrap, make lint, etc.)
└── .gitignore                    # Iron-clad credential & state file exclusions
```

---

## 🚀 Quick Start (Developer Ergonomics)

We provide a specialized `Makefile` interface to streamline complex shell operations:

```bash
# Verify tooling, dependencies, and lint repository syntax
make check

# View active targets and running cluster status
make status

# Deploy core foundational Docker network and Traefik router on 'homelab'
make deploy-core
```

---

## 🔒 Security & Secrets Warning
**NEVER** commit plain-text passwords, SSH private keys, tokens, or `.env` files directly into this repository. All confidential parameters must rely on encrypted structures (such as SOPS, HashiCorp Vault, or strict Git-excluded templates).
