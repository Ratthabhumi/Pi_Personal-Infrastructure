Current observation - 5 November 2026 (live host audit): storage acceptance PASS, Docker data-root PASS, Node Exporter loopback HTTP 200 PASS, SSH/Tailscale/Docker PASS. The earlier monitoring failure is closed; use the 24/7 host hardening action in OWNER_DECISION_PACKET.md. Earlier snapshots below are historical.

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
