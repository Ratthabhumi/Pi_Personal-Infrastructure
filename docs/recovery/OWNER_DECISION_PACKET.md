# Owner decisions and one immediate action

Only immediate action needed: run the staged read-only storage inspection through the existing SSH route. The staged shell verifies the Python script SHA-256, requests sudo interactively, inspects only the approved approximately 1 TB ext4 UUID read-only/no replay and writes sanitized JSON under the login user's private state directory. It does not format, permanently mount, install, deploy, change SSH/Tailscale/firewall or read secret contents.

```powershell
ssh -t mew@homelab bash /home/mew/.local/share/homelab-recovery-20261105/inspect-approved-storage.sh
```

Enter the Ubuntu password locally in that terminal only. Tell Codex the inspection ran; do not paste credentials/raw application files. If it fails, preserve the result and stop; do not rerun bootstrap or format. Root is required because the normal account cannot inspect the unmounted block device. No passwordless sudo is requested. Script digest and private UUID binding are staged locally on the host; public Git contains neither secret values nor host UUID.

Remaining decisions after evidence: permanent data mount/verified restore selection; independent home uplink if hotspot leaves; physical recovery contact; explicitly bounded package/Docker/firewall/lid changes after inspection; privately reviewed credential/backup contracts. Do not accept unresolved risks merely to declare travel-ready. No subscription, full-stack deployment, trading or automatic-update change has been approved/executed.
