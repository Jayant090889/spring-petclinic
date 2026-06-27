# Rollback Plan — Rancher to AKS Migration

## Rollback Decision Tree

```
Is error rate > 5% for 3+ minutes?          YES → ROLLBACK IMMEDIATELY
Is p95 latency > 1000ms for 5+ minutes?     YES → ROLLBACK IMMEDIATELY
Are DB connections failing from AKS pods?    YES → ROLLBACK IMMEDIATELY
Is there a P1 Tetragon security alert?       YES → ROLLBACK IMMEDIATELY
Has business team reported critical failure? YES → ROLLBACK IMMEDIATELY
Are all above NO?                                 → CONTINUE, MONITOR
```

## Rollback Trigger Thresholds
| Metric | Warning | Rollback Trigger |
|--------|---------|-----------------|
| HTTP error rate | > 1% | > 5% for 3 min |
| Response time p95 | > 500ms | > 1000ms for 5 min |
| Pod restart count | > 2 | > 5 in 10 min |
| DB connection pool | > 80% | > 95% |
| Tetragon: unexpected exec | Any | Any — immediate |

---

## Rollback Steps (Target: < 10 minutes total)

| Step | Time | Command | Expected Result |
|------|------|---------|-----------------|
| 1 | T+0 | Declare rollback — notify war room | Slack: `@channel ROLLBACK INITIATED` |
| 2 | T+1 | Scale up Rancher source | `kubectl scale deploy petclinic --replicas=2 -n petclinic-source` |
| 3 | T+2 | Verify source pods running | `kubectl get pods -n petclinic-source` — 2/2 Running |
| 4 | T+3 | Health check source | `curl http://rancher-petclinic/actuator/health` — UP |
| 5 | T+4 | Revert DNS A record | `az network dns record-set a update --ipv4-address <RANCHER-IP>` |
| 6 | T+6 | Verify DNS revert | `dig petclinic.example.com` — returns Rancher IP |
| 7 | T+8 | End-to-end smoke test on source | `curl https://petclinic.example.com/actuator/health` — UP |
| 8 | T+10 | Notify stakeholders | ServiceNow incident + email to business team |

---

## Post-Rollback Actions
- [ ] Raise P1 incident in ServiceNow — document symptoms, timeline, evidence
- [ ] Preserve AKS pod logs: `kubectl logs deployment/petclinic -n petclinic --previous > rollback_pod_logs.txt`
- [ ] Preserve Tetragon events from the failed window
- [ ] Schedule post-mortem within 24 hours — blameless format
- [ ] Root cause analysis before rescheduling cutover
- [ ] Update risk register with new blocker items
