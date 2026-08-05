# Site Reliability & Observability Layer

In alignment with **Observability Driven Development (ODD)**, no service is running properly unless it is actively reporting its vitals.

## Core SRE Components
1. **Prometheus / VictoriaMetrics**: Time-series metrics engine polling machine nodes (CPU, RAM, Disk temperature, Network throughput) and Docker container utilization every 15 seconds.
2. **Grafana**: Enterprise analytics visualization dashboard providing rich telemetry views.
3. **Grafana Loki & Promtail**: Distributed log aggregator. Instead of running `ssh mew@homelab docker logs <id>`, logs are instantly streamlined directly into Grafana for querying with LogQL.
4. **Node Exporter & cAdvisor**: Light daemon agents providing bare-metal kernel hardware statistics and Docker container metrics.
5. **Uptime Kuma / Alertmanager**: Active uptime monitor pinging endpoints and firing instant Telegram/Discord notifications if latency spikes or services break.
