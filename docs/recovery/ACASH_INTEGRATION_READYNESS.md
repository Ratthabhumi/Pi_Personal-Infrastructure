# ACASH integration readiness

Date: 5 November 2026.

HOST: **READY**. The Pi/Acer host side is accepted for a separately managed ACASH market-data workload. See [PI_HOST_READY_FOR_ACASH.md](PI_HOST_READY_FOR_ACASH.md) for the host contract: storage, `/data/acash`, resource budget, scheduling semantics, network expectations and secret handling.

APPLICATION: **NOT DEPLOYED**. Windows remains the development/validation workstation. This repository created only an empty, root-only `/data/acash`. It installs no collector, scheduler, provider credential, database, research job, dashboard or trading process. The ACASH collector belongs to the ACASH repository (ACASH PR #80), including its schedule, backfill logic, data-quality rules and warehouse layout.

GOVERNANCE: `NO_REAL_ORDERS=true` and zero capital authority are unchanged. Host readiness is not data admission, research approval, paper/live authority or evidence of returns.

24/7 SEMANTICS: the host runs continuously; data collection follows market schedules and provider entitlements. EOD data is collected after the US close, and missed dates are backfilled by ACASH when the provider or uplink returns. Pi does not buffer or replay data for ACASH.

BLOCKERS carried by the host: the owner 24/7 hardening action (UFW + no-suspend) is prepared but not executed; off-device backup target is missing; the only uplink is an iPad hotspot.

NEXT: deploy from the ACASH repository under a separate workload scope, with a non-root identity, container limits, `/data/acash` only, and ACASH-owned secrets/backfill. This repository will not deploy it.
