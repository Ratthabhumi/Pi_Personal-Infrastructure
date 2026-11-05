# Travel remote-access runbook

Current status **NOT TRAVEL-READY**. FACT: SSH/Tailscale are reachable now; sole owner-reported internet is iPad hotspot. EVIDENCE: default route uses Wi-Fi; no independent always-on uplink or remote-power recovery verified. A hotspot that leaves the home disconnects this Exit Node.

Before departure: verify an independently powered continuous uplink, a trusted physical recovery contact, power/cooling/lid policy and actual client egress; test reconnection from a separate network while a recovery path exists. Record backup restore evidence and a service-specific rollback. Do not reboot remotely to test before that path exists. Do not print Tailscale auth material or share private keys.

If access drops: preserve Tailscale identity/config; check hotspot/uplink and power locally through the trusted owner; avoid reinstall/reset/key replacement as a first step. New Windows key login is working; original password login was retained. The owner key-install action created a private authorized_keys backup; removal/rollback should be done interactively only after another validated access method exists.

During travel: avoid unattended package/container upgrades, new public management ports, stack-wide restarts, firewall rewrites and storage changes. Existing unattended-upgrades was already active; this task did not enable/disable it. Decide its safe operating/recovery policy before departure. No guarantee of access in another country or of bypassing network restrictions is made.
