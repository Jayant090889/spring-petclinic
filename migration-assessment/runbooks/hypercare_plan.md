# Post-Migration Hypercare Plan — 72 Hours

## Hypercare Phases

| Phase | Duration | Cadence | On-Call Coverage |
|-------|----------|---------|-----------------|
| Intensive | H+0 to H+4 | Every 5 minutes | Senior engineer active, all teams available |
| Standard | H+4 to H+24 | Every 15 minutes | On-call engineer, escalation path active |
| Reduced | H+24 to H+72 | Every 30 minutes | Standard on-call rotation |
| Normal ops | H+72+ | Standard SLA | Normal rotation, hypercare closed |

---

## Key Metrics and Dashboards

| Metric | Tool | Dashboard | Warning | Critical |
|--------|------|-----------|---------|----------|
| HTTP error rate | Grafana | AKS HTTP Overview | > 1% | > 5% |
| Response time p95 | Azure Monitor | Container Insights | > 500ms | > 1000ms |
| Pod restart count | Grafana | Kubernetes / Compute | > 2 | > 5 |
| DB connection pool | Prometheus | MySQL Exporter | > 80% | > 95% |
| CPU utilisation | Azure Monitor | Node metrics | > 70% | > 90% |
| Memory utilisation | Azure Monitor | Node metrics | > 75% | > 90% |
| HPA replica count | Grafana | HPA Overview | At maxReplicas | — |
| Tetragon: unexpected exec | Tetragon / SIEM | Security Events | Any | Any — P1 |
| Tetragon: unknown egress | Tetragon / SIEM | Security Events | Any | Any — P1 |

---

## Escalation Matrix

| Severity | Definition | Response Time | Primary | Escalate To |
|----------|-----------|---------------|---------|-------------|
| P1 — Critical | Service down or security alert | 15 min | On-call engineer | Platform Lead + Security Lead |
| P2 — High | Degraded performance, error rate elevated | 30 min | On-call engineer | Platform Lead |
| P3 — Medium | Non-critical issue, monitoring anomaly | 2 hours | On-call engineer | Team lead next business day |

---

## Go/No-Go Criteria — Close Hypercare at H+72

All of the following must be true before declaring hypercare complete:

- [ ] Zero P1 incidents in the last 48 hours
- [ ] HTTP error rate < 0.1% sustained for 24 hours
- [ ] Response time p95 < 300ms over 24-hour period
- [ ] No Tetragon alerts for unexpected process execution or unknown egress
- [ ] Pod restarts < 2 in last 24 hours (excluding expected deployments)
- [ ] HPA has not hit maxReplicas limit unexpectedly
- [ ] Business application team has provided written sign-off
- [ ] All P2/P3 issues from hypercare period have owners and remediation dates

---

## Tetragon-Specific Monitoring During Hypercare

Based on OCBC SIEM experience, the following Tetragon event patterns are
monitored with immediate P1 escalation:

1. **Unexpected shell execution** — any `execve` of `/bin/sh`, `/bin/bash` or `/bin/ash`
   from within petclinic pods during production hours
2. **Unknown egress destination** — TCP connection attempts to IPs not matching
   approved CiliumNetworkPolicy destinations
3. **Privilege escalation attempt** — `setuid`, `setgid` or capability changes
   from UID 1001 (the petclinic non-root user)
4. **Suspicious binary execution** — `curl`, `wget`, `nc`, `nmap` executed
   from within application pods
5. **High-frequency DNS queries** — > 100 DNS queries per minute from a single
   pod (potential DNS tunnelling indicator)

Tetragon events are streamed to the SIEM workspace for correlation with
Azure Monitor and ingress WAF logs.
