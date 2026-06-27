# Rancher to AKS Cutover Runbook — Spring PetClinic

## Document Control
| Field | Value |
|-------|-------|
| Application | Spring PetClinic |
| Source environment | Rancher Desktop (k3d simulation of on-premises) |
| Target environment | AKS aks-petclinic-prod (southeastasia) |
| Runbook version | 1.0.0 |
| Runbook owner | Jayant Prateek (AVP Cloud Engineering) |
| Approvers | Platform Lead, Security Lead, Business Owner |
| Cutover window | Saturday 02:00–06:00 SGT (MAS low-risk maintenance window) |
| Change record | ServiceNow CHG-2024-0847 |

---

## Pre-Cutover Checklist — T-48 Hours

### Infrastructure readiness
- [ ] AKS cluster healthy: `kubectl get nodes` — all nodes in `Ready` state
- [ ] All petclinic pods running on AKS: `kubectl get pods -n petclinic` — all `Running`
- [ ] Azure Database for MySQL reachable from AKS pods: connection test from netshoot pod
- [ ] ACR image tag confirmed: `az acr repository show-tags --name acrpetclinicprod --repository petclinic`
- [ ] TLS certificate valid on AKS ingress: `curl -vI https://petclinic.example.com` — no cert errors
- [ ] NGINX ingress external IP stable: `kubectl get svc -n ingress-nginx`

### Application readiness
- [ ] AKS non-prod smoke tests passing: `curl https://petclinic-dev.example.com/actuator/health` returns `{"status":"UP"}`
- [ ] Database migration complete and data validated by application team
- [ ] Secrets migrated to Azure Key Vault and CSI driver syncing correctly
- [ ] Tetragon runtime monitoring active: `kubectl exec ds/tetragon -n kube-system -c tetragon -- tetra getevents -o compact`

### Operational readiness
- [ ] Rollback tested in non-prod — `helm rollback petclinic -n petclinic` executes without error
- [ ] On-call engineer confirmed, briefed, and has runbook access
- [ ] Monitoring dashboards open: Grafana (http://grafana.internal), Azure Monitor portal
- [ ] Stakeholder notification sent via ServiceNow and email
- [ ] War room Slack channel `#petclinic-migration` active

---

## Pre-Cutover Checklist — T-2 Hours

- [ ] Reduce DNS TTL to 60 seconds: update zone file, verify with `dig +trace petclinic.example.com`
- [ ] Final baseline response time on Rancher source: `curl -w "%{time_total}" http://rancher-petclinic/actuator/health`
- [ ] Confirm AKS replica count: `kubectl get deployment petclinic -n petclinic` shows 2/2
- [ ] All approvers confirmed available on call
- [ ] Azure Monitor alert rules active for AKS cluster

---

## Cutover Steps

| Step | Time | Action | Command | Expected Result | Owner |
|------|------|--------|---------|-----------------|-------|
| 1 | T+0 | Pause CI/CD pipelines to Rancher | Disable GitHub Actions deploy job | No new deployments to source | DevOps |
| 2 | T+5 | Final health check on source | `curl http://rancher-petclinic/actuator/health` | `{"status":"UP"}` | Engineer |
| 3 | T+10 | Scale down Rancher source | `kubectl scale deploy petclinic --replicas=0 -n petclinic-source` | Pods terminating |Engineer |
| 4 | T+12 | Verify source scaled down | `kubectl get pods -n petclinic-source` | No running pods | Engineer |
| 5 | T+15 | Switch DNS A record to AKS | `az network dns record-set a update --ipv4-address <AKS-IP>` | DNS update confirmed | NetOps |
| 6 | T+20 | Verify DNS propagation | `dig petclinic.example.com` | Returns AKS ingress IP | Engineer |
| 7 | T+22 | End-to-end smoke test | `curl -sf https://petclinic.example.com/actuator/health` | `{"status":"UP"}` | QA |
| 8 | T+25 | Application functional test | Log in, create owner, create pet — verify data persists | All actions succeed | QA |
| 9 | T+30 | Performance validation | `k6 run --vus 50 --duration 2m load-test.js` | p95 < 500ms, error rate < 1% | Engineer |
| 10 | T+35 | GO/NO-GO decision | All above checks pass? | Proceed to hypercare | All |

---

## GO / NO-GO Decision Criteria

**GO if ALL of the following are true:**
- HTTP error rate < 1% for 5 consecutive minutes
- Response time p95 < 500ms
- All smoke tests returning HTTP 200
- No P1 Tetragon alerts (unexpected shell exec or egress)
- Business team confirms application functional

**NO-GO / Rollback if ANY of the following occur:**
- Error rate > 5% sustained for 3 minutes
- Response time p95 > 1000ms sustained for 5 minutes
- Database connection errors from AKS pods
- Critical Tetragon alert (unexpected process execution)
- Business validation failure

---

## Post-Cutover Validation (T+45 to T+120)
- [ ] Monitor Grafana dashboard — error rate, latency, pod restarts
- [ ] Review Tetragon events for unexpected behaviour
- [ ] Confirm Azure Monitor Container Insights showing healthy metrics
- [ ] Application team signs off on functional verification
- [ ] Update ServiceNow change record to Implemented

---

## Source-to-Target Component Mapping

| Component | Source (Rancher/k3d) | Target (AKS) | Migration Action | Owner |
|-----------|---------------------|--------------|-----------------|-------|
| Namespace | petclinic | petclinic | Recreate with same name + AKS labels | Platform Team |
| ServiceAccount | petclinic-sa | petclinic-sa | Recreate + add workload identity annotation | Platform Team |
| Deployment | petclinic (2 replicas) | petclinic (2 replicas, ACR image) | Rehost with updated image registry | Platform Team |
| Service | petclinic-svc (ClusterIP) | petclinic-svc (ClusterIP) | Direct rehost | Platform Team |
| ConfigMap | petclinic-config | petclinic-config | Update MYSQL_HOST to Azure DB FQDN | Platform Team |
| Secret (DB creds) | petclinic-db-secret | Azure Key Vault + CSI Driver | Migrate to Key Vault, remove K8s Secret | Security Team |
| Secret (TLS) | petclinic-tls | AKS cert-manager or Key Vault | Provision new cert on AKS | Security Team |
| Ingress | nginx (k3d) | nginx-ingress (AKS) | Update ingressClassName, TLS secret, hostname | Platform Team |
| PVC (MySQL data) | mysql-data (hostPath) | Azure Disk (Premium_LRS) | Data migration via mysqldump/restore | DBA |
| RBAC Role | petclinic-role | petclinic-role | Direct rehost | Platform Team |
| NetworkPolicy | none | default-deny + CiliumNetworkPolicy | New — no source equivalent | Platform Team |
| HPA | none | petclinic-hpa (2–5 replicas) | New — no source equivalent | Platform Team |
| PDB | none | petclinic-pdb (minAvailable: 1) | New — no source equivalent | Platform Team |
| Node affinity | none | userPool node selector | New — route to user nodepool | Platform Team |

## Workload Classification

| Workload | Pattern | Rationale |
|----------|---------|-----------|
| petclinic Deployment | **Rehost** | Stateless Java app — direct lift to AKS with image change |
| MySQL StatefulSet | **Replatform** | Replace with Azure Database for MySQL — managed, HA, backups included |
| Kubernetes Secrets | **Replatform** | Migrate to Azure Key Vault for MAS TRM compliance |
| NGINX Ingress | **Replatform** | Replace self-managed with AKS-managed NGINX ingress controller |
| CI/CD (manual kubectl) | **Refactor** | Replace with GitHub Actions automated pipeline |
| HAProxy (edge) | **Retire** | Not required for this workload — NGINX covers all routing needs |
