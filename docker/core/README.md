# Core Infrastructure Layer

This layer acts as the **Gateway, Router, and Edge Controller** for all traffic entering our infrastructure.

## Planned Deployments Here
1. **Traefik Reverse Proxy**: Automatically intercepts requests from Tailscale mesh network and directs them to internal ports while provisioning automatic internal HTTPS certificates.
2. **Local DNS Resolver (Optional)**: Pi-hole or AdGuard Home for whole-network DNS caching, DNS-over-HTTPS (DoH), and security filtering.
3. **Container Management Engine**: Portainer CE / Dockge for visual inspection of lightweight Docker deployment states.

## Why is Core Separated?
In a DevOps resilience model, your core ingress router must **never** be tied to application-level containers (like AI chat bots or media centers). If an application crashes or runs out of RAM, Traefik and edge routing must remain 100% online so SRE monitors and SSH terminals can still route without interruption.
