Current observation — 5 November 2026: authorized format and /data acceptance passed; Docker/Compose/Ansible are installed, monitoring host HTTP failed. Do not run the clean/restore packets again. Use the service-only finish action in OWNER_DECISION_PACKET.md. Earlier snapshots below are historical.

Current decision update — 5 November 2026: owner explicitly approved clean formatting of the old-UUID-bound 1 TB partition and new /data storage. Legacy restoration/inspection instructions are superseded. Execution remains pending interactive sudo. See OWNER_CLEAN_STORAGE_DECISION_20261105.md and OWNER_DECISION_PACKET.md. Earlier host snapshots below remain evidence of their observation time.

# Travel remote-access runbook

Current status **NOT TRAVEL-READY**. FACT: SSH/Tailscale are reachable now; sole owner-reported internet is iPad hotspot. EVIDENCE: default route uses Wi-Fi; no independent always-on uplink or remote-power recovery verified. A hotspot that leaves the home disconnects this Exit Node.

Before departure: verify an independently powered continuous uplink, a trusted physical recovery contact, power/cooling/lid policy and actual client egress; test reconnection from a separate network while a recovery path exists. Record backup restore evidence and a service-specific rollback. Do not reboot remotely to test before that path exists. Do not print Tailscale auth material or share private keys.

If access drops: preserve Tailscale identity/config; check hotspot/uplink and power locally through the trusted owner; avoid reinstall/reset/key replacement as a first step. New Windows key login is working; original password login was retained. The owner key-install action created a private authorized_keys backup; removal/rollback should be done interactively only after another validated access method exists.

During travel: avoid unattended package/container upgrades, new public management ports, stack-wide restarts, firewall rewrites and storage changes. Existing unattended-upgrades was already active; this task did not enable/disable it. Decide its safe operating/recovery policy before departure. No guarantee of access in another country or of bypassing network restrictions is made.
