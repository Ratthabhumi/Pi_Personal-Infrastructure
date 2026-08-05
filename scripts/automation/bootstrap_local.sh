#!/usr/bin/env bash
# ==============================================================================
# LOCAL GITOPS SELF-BOOTSTRAPPING & RECONCILIATION ENGINE
# Designed for execution directly inside mew@homelab via terminal or cron
# ==============================================================================

set -e # Exit immediately on any undocumented execution failure

echo "==================================================================="
echo "   🛡️ HOMELAB SELF-PROVISIONING & GITOPS RECONCILIATION ENGINE     "
echo "==================================================================="

# 1. Ensure core Python & Ansible automation runtimes exist natively on Ubuntu
echo "[1/3] Checking OS prerequisite packages (Git & Ansible)..."
if ! command -v ansible-playbook &> /dev/null; then
    echo "  -> Ansible missing! Initializing localized package provisioning..."
    sudo apt-get update -y
    sudo apt-get install -y git ansible python3-apt software-properties-common
    echo "  -> [OK] Ansible runtime successfully injected."
else
    echo "  -> [OK] Ansible engine detected natively."
fi

# 2. Synchronize current working state with Remote Git Repository (Optional if Git URL exists)
echo "[2/3] Checking git repository sync status..."
if git rev-parse --is-inside-work-tree &> /dev/null; then
    if git remote get-url origin &> /dev/null; then
        echo "  -> Pulling latest infrastructure declaration state from remote Git origin..."
        git pull origin main || git pull origin master || echo "  -> [Notice] Using current local branch filesystem state."
    else
        echo "  -> [Notice] No remote origin attached yet. Relying on current folder contents."
    fi
fi

# 3. Execute Ansible locally to configure Ubuntu OS and Docker Engine
echo "[3/3] Launching local Ansible Playbook execution against 'homelab'..."
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/00_bootstrap_server.yml \
    --connection=local \
    --limit=homelab \
    --extra-vars="ansible_python_interpreter=/usr/bin/python3"

echo "==================================================================="
echo "   ✅ HOMELAB RECONCILIATION COMPLETE: ALL SYSTEMS NOMINAL         "
echo "==================================================================="
