Current observation — 5 November 2026: authorized format and /data acceptance passed; Docker/Compose/Ansible are installed, monitoring host HTTP failed. Do not run the clean/restore packets again. Use the service-only finish action in OWNER_DECISION_PACKET.md. Earlier snapshots below are historical.

Current decision update — 5 November 2026: owner explicitly approved clean formatting of the old-UUID-bound 1 TB partition and new /data storage. Legacy restoration/inspection instructions are superseded. Execution remains pending interactive sudo. See OWNER_CLEAN_STORAGE_DECISION_20261105.md and OWNER_DECISION_PACKET.md. Earlier host snapshots below remain evidence of their observation time.

# Exit Node acceptance

| Test | Result | Evidence/limit |
|---|---|---|
| Windows SSH key authentication | PASS | Live whoami=mew, hostname=homelab, Linux |
| Tailscale backend online | PASS | Live JSON backend Running, self Online=true |
| Exit routes advertised | PASS | Both default routes present in preferences |
| Exit option visible | PASS | Self ExitNodeOption=true; not mobile egress proof |
| IPv4/IPv6 forwarding | PASS | Both proc sysctls equal 1 |
| DNS | PASS | github.com resolution exit zero; IP suppressed |
| SSH/Tailscale enabled | PASS | systemctl snapshot |
| Client egress/exit approval end-to-end | NOT TESTED | No authorized mobile client observation this session |
| Effective UFW/forwarding chain | BLOCKED | Needs privileged inspection |
| Post-Docker network regression | NOT TESTED | Docker not installed; no firewall/network changes |
| Restart/reboot reconnection | NOT TESTED | No validated independent recovery path |
| Travel independent uplink | BLOCKED | Owner reports only iPad hotspot; active route uses Wi-Fi |

FACT: the host cannot remain an online Thailand Exit Node if its only upstream hotspot leaves. A paid/independent replacement is an owner decision; no service/billing was created. No remote-access settings or Tailscale identity changed.
