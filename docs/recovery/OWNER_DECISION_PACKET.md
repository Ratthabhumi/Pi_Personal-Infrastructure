# One action — finish monitoring only

**HDD formatting succeeded. Do not run Invoke-OwnerClean.ps1 again.** Docker/Compose/Ansible are installed. Only monitoring HTTP acceptance is currently failing; the original result's foundation=NOT_EXECUTED field was inaccurate.

Run this NEW service-only packet in Windows PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Users\MewMew\.codex\worktrees\homelab-recovery\Pi_Personal-Infrastructure\scripts\recovery\Invoke-OwnerFinish.ps1"
```

Owner sudo is required for Docker inspection/recreation; enter the password locally only. No formatter, partition, mount/fstab write, package install, engine restart or attempt-marker reset is present. It first proves the existing UUID/data-root and exact source/runtime state. If metrics work inside the exporter namespace but fail on the host, it may recreate ONLY this reviewed monitoring service once.

The candidate uses host networking with the process explicitly listening on 127.0.0.1:9100 and no published ports. It therefore shares host-network visibility/egress instead of an internal bridge. It retains non-root UID, no capabilities, no-new-privileges, read-only filesystem, CPU/PID/RAM limits and only read-only /proc,/sys mounts. No Docker socket/private data/credentials or public dashboard. Unknown cause/profile drift stops without changes. The owner action runs this concrete scoped repair, not a generic shell/deployment.

Wait for FINISH_RESULT and send only that sanitized summary. If it fails, stop; never rerun clean or clear markers. The original clean report is retained and finish-result.json is separate. Root finish execution and successful metrics remain pending; original storage is already accepted. External client Exit Node, independent uplink, reboot recovery and off-disk backups remain separate work.
