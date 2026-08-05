# ==============================================================================
# HOMELAB INFRASTRUCTURE AUTOMATION CONTROLLER (MAKEFILE)
# Single point of execution for Operations, SRE, and Maintenance Tasks
# ==============================================================================

.PHONY: help check status bootstrap apply-local deploy-core backup docs lint

# Default target executes help display
help:
	@echo "==================================================================="
	@echo "    HOME-LAB PLATFORM ENGINEERING & DEV-OPS MANAGEMENT INTERFACE   "
	@echo "==================================================================="
	@echo "Available commands:"
	@echo "  make check          - Check prerequisites (ansible, docker, git, tailscale)"
	@echo "  make bootstrap      - Run initial server hardening and package provisioning via Ansible"
	@echo "  make apply-local    - Run autonomous local GitOps bootstrap directly ON the server"
	@echo "  make deploy-core    - Spin up essential routing (Traefik/DNS) on homelab server"
	@echo "  make deploy-obs     - Spin up SRE Observability Stack (Prometheus, Grafana, Loki)"
	@echo "  make lint           - Validate YAML, scripts, and Markdown styling across repo"
	@echo "  make docs           - Automatically re-generate systems inventory markdown"
	@echo "  make ssh            - Quick direct SSH connection into mew@homelab via Tailscale"
	@echo "==================================================================="

ssh:
	@ssh mew@homelab

check:
	@echo "[*] Checking engineering tooling on local workstation..."
	@which git >/dev/null && echo "  [OK] Git installed." || echo "  [FAIL] Git missing!"
	@which ssh >/dev/null && echo "  [OK] SSH installed." || echo "  [FAIL] SSH missing!"
	@echo "[*] Workspace structural checks complete."

bootstrap:
	@echo "[*] Executing zero-touch OS bootstrap via Ansible..."
	ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/00_bootstrap_server.yml

apply-local:
	@echo "[*] Executing Local GitOps self-provisioning script..."
	bash scripts/automation/bootstrap_local.sh

deploy-core:
	@echo "[*] Deploying Gateway, Traefik Reverse Proxy, and Core DNS layer..."
	ssh mew@homelab 'mkdir -p ~/.homelab/docker/core'
	scp -r docker/core/* mew@homelab:~/.homelab/docker/core/
	ssh mew@homelab 'cd ~/.homelab/docker/core && docker compose up -d --remove-orphans'

deploy-obs:
	@echo "[*] Deploying Observability & Telemetry stack (SRE Layer)..."
	ssh mew@homelab 'mkdir -p ~/.homelab/docker/observability'
	scp -r docker/observability/* mew@homelab:~/.homelab/docker/observability/
	ssh mew@homelab 'cd ~/.homelab/docker/observability && docker compose up -d --remove-orphans'

# ------------------------------------------------------------------------------
# LOCAL SERVER CONTAINER COMMANDS (Run directly within mew@homelab terminal)
# ------------------------------------------------------------------------------
core-up:
	@echo "[*] Launching Core Gateway (Traefik & Portainer)..."
	cd docker/core && docker compose up -d --remove-orphans

core-down:
	@echo "[*] Shutting down Core Gateway..."
	cd docker/core && docker compose down

obs-up:
	@echo "[*] Launching SRE Observability & Telemetry Stack..."
	cd docker/observability && docker compose up -d --remove-orphans
