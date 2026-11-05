# One owner action — clean the approved HDD and install minimal foundation

Deletion is already authorized. Only interactive sudo authentication remains; no further deletion confirmation or password sharing is required. The previously staged read-only inspection is superseded. Do not execute that old packet.

Run this ONE new command from Windows PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "C:\Users\MewMew\.codex\worktrees\homelab-recovery\Pi_Personal-Infrastructure\scripts\recovery\Invoke-OwnerClean.ps1"
```

The Windows wrapper selects the unique online homelab peer from the existing Tailscale connection if MagicDNS is unavailable, while retaining the existing homelab host key and StrictHostKeyChecking=yes. It never edits DNS, SSH trust or authentication. The remote packet verifies all source SHA-256 hashes, authenticates sudo locally, then rechecks the approved UUID, approximately 1 TB size, partition/system/installer exclusions and absence of mounts before formatting ONLY that partition. It sets HOMELAB_DATA, creates a new UUID/fstab mount at /data, verifies synthetic I/O, creates root-only directories, then installs official Docker/Compose/Ansible and the loopback-only bounded monitoring profile. It does not restore applications/secrets or deploy ACASH. Source files are linked in Draft PR #1 for review. No repartition, OS reinstall, LVM growth, reauthentication, public dashboard or passwordless sudo.

Wait for the result marker and tell Codex **clean setup ran**. Do not paste passwords or the raw private JSON. The JSON is under the login user's private state directory and includes the actual new UUID/phase/commands for Codex to sanitize. If BLOCKED/failed/disconnected, stop: do not run again, remove attempt markers or retry formatting. The persistent root marker prevents a second attempt; package/service repair must be based on the current result.

Remaining decisions: independent continuous home uplink if the iPad leaves, physical recovery path, off-disk backups and future service/data scopes. None are solved by formatting HDD. Existing unattended-upgrades was already active and is not enabled/disabled here. Real mobile Exit Node egress and reboot survival still require actual evidence.
