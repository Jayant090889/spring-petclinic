# NGINX vs HAProxy Ingress — Migration Design

## Decision Summary
For the Rancher-to-AKS migration, **NGINX Ingress Controller** is selected as the primary
ingress solution. HAProxy is documented here as the comparison and the on-premises source pattern.

## NGINX Ingress Controller (Selected for AKS)

### Why NGINX for AKS
- Native support via AKS Application Routing addon
- Annotation-driven configuration — no sidecar required
- Well-supported by Azure and CNCF ecosystem
- Simpler operational model for platform team managing multiple workloads

### Key NGINX Annotations Used
| Annotation | Value | Purpose |
|-----------|-------|---------|
| nginx.ingress.kubernetes.io/ssl-redirect | "true" | Force HTTPS |
| nginx.ingress.kubernetes.io/limit-rps | "100" | Rate limiting |
| nginx.ingress.kubernetes.io/proxy-read-timeout | "60" | Backend timeout |
| nginx.ingress.kubernetes.io/proxy-body-size | "10m" | Upload limit |

## HAProxy Ingress Controller (On-Premises Source Pattern)

### Where HAProxy Was Used On-Prem
HAProxy acted as the **edge gateway** in the on-premises Rancher environment — handling
Layer 4 TCP routing, complex health checks, and sticky sessions for legacy Java workloads.

### HAProxy Annotations (for reference/migration mapping)
| HAProxy Annotation | NGINX Equivalent | Notes |
|-------------------|-----------------|-------|
| haproxy.org/timeout-connect | proxy-connect-timeout | TCP connection timeout |
| haproxy.org/timeout-server | proxy-read-timeout | Backend response timeout |
| haproxy.org/load-balance | nginx.ingress.kubernetes.io/upstream-hash-by | Load balancing algorithm |
| haproxy.org/forwarded-for | nginx.ingress.kubernetes.io/forwarded-for-header | Client IP forwarding |
| haproxy.org/check | nginx.ingress.kubernetes.io/healthcheck-path | Backend health check |
| haproxy.org/sticky-session | nginx.ingress.kubernetes.io/affinity: "cookie" | Session persistence |

### When to Keep HAProxy
- Workloads requiring TCP-level (Layer 4) routing — not HTTP
- Complex health check logic with custom intervals per backend
- Legacy applications requiring sticky sessions with custom cookie names
- High-throughput scenarios where HAProxy's performance profile is needed (>50k RPS)

## DNS Cutover Design

### Pre-Cutover (T-48 hours)
1. Reduce DNS TTL to 60 seconds
2. Deploy to AKS, validate all health checks pass
3. Confirm TLS certificate valid on AKS ingress

### Cutover Sequence
1. Scale Rancher source to 0 replicas (prevents split-brain writes)
2. Update DNS A record to point to AKS NGINX ingress external IP
3. Wait for TTL propagation (60 seconds with reduced TTL)
4. Run smoke tests against new AKS endpoint
5. Monitor error rate for 30 minutes — rollback trigger if >2%

### Rollback
- Revert DNS A record to Rancher load balancer IP
- Scale Rancher source back to 2 replicas
- Total rollback time: <5 minutes with 60s TTL
