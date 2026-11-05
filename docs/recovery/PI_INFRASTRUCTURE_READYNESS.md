## Corrected v2 — actual preflight result

Owner sudo authentication DID succeed. The original invocation stopped at live-storage-safety-gates / PHYSICAL_PARENT_NOT_PROVEN with formatting=NOT_EXECUTED and no mkfs command in its report. Old filesystem remains visible; SSH/Tailscale active. Verified on the actual host: PATH-only lsblk JSON without --tree returns 9 flat entries; adding --tree returns 3 disk trees and the same physical-parent gate passes. This was a source bug, not evidence of a wrong disk or failed password.

Production snapshot now explicitly requests --tree. Seven Linux regressions pass, including an integration check of real lsblk parent edges. v2 uses a separate bundle/result while retaining original evidence and the same root one-attempt lock/marker; it never clears a marker. The corrected root action must still verify its absence and every safety gate before formatting. The local Windows command below is updated to v2. No actual format, new UUID, mount, packages or monitoring acceptance has occurred. The v2 owner packet prints sanitized result fields so a preflight failure is visible instead of only a closed connection. See evidence/clean-topology-fix-20261105.json.

# Pi minimal readiness

PASS: authorized SSH key route; source preparation; current old-UUID match and unmounted approximately 1 TB layout observed without privilege. CI/mock results are source checks only.

PREPARED: single authorized owner-root format/mount/foundation/monitoring packet with fail-closed identity gates, one-attempt record, signed package sources, HDD-backed Docker, log limits, exact mount dependency and loopback non-root monitoring.

BLOCKED: interactive sudo execution. NOT EXECUTED: formatting/new UUID/fstab/mount/Docker/Ansible/monitoring. NOT TESTED: service restart/reboot/client Exit Node/off-disk backup restore. No complete/production/travel-ready claim.
