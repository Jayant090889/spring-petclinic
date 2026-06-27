# Test Evidence — Rancher to AKS Migration Assessment

> This document is your evidence log. After completing each step,
> paste the command output here. This is what the assessors review.

---

## Module 1 — Discovery & Inventory

### Task 1.1 — Source cluster running
```
# Paste output of:
# kubectl get all -A
# kubectl get nodes -o wide
PASTE HERE
```

### Task 1.2 — Crawler output
```
# Paste output of:
# python3 k8s_inventory_crawler.py --input source_export.yaml
PASTE HERE
```

### Task 1.3 — Dependency classification
See: `discovery/dependency_summary.md`

---

## Module 2 — Containerisation

### Docker build
```
# Paste: docker build -t petclinic:v1 .
PASTE HERE
```

### Health check
```
# Paste: curl http://localhost:8080/actuator/health
PASTE HERE
```

### Trivy scan
```
# Paste: trivy image petclinic:v1 --severity HIGH,CRITICAL
PASTE HERE
```

---

## Module 3 — Kubernetes Manifests

### Helm deploy
```
# Paste: helm install petclinic ./helm/petclinic -f values.onprem.yaml
PASTE HERE
```

### Pods running
```
# Paste: kubectl get pods -n petclinic
PASTE HERE
```

### HPA active
```
# Paste: kubectl get hpa -n petclinic
PASTE HERE
```

---

## Module 4 — Ingress

### NGINX ingress deployed
```
# Paste: kubectl describe ingress -n petclinic
PASTE HERE
```

### Curl to ingress
```
# Paste: curl -v -H "Host: petclinic.local" http://EXTERNAL-IP/actuator/health
PASTE HERE
```

---

## Module 5 — Egress & Cilium

### Network policy applied
```
# Paste: kubectl get networkpolicies -n petclinic
# Paste: kubectl get ciliumnetworkpolicies -n petclinic
PASTE HERE
```

### Egress test matrix
| Flow | Command | Result | Screenshot |
|------|---------|--------|-----------|
| petclinic → MySQL (allowed) | `curl mysql:3306` from pod | ✓ Connected | |
| petclinic → partner API (allowed) | `curl https://api.partner-bank.com` | ✓ 200 OK | |
| petclinic → google.com (denied) | `curl https://google.com` | ✗ Connection refused | |
| ingress → petclinic (allowed) | External curl to app | ✓ 200 OK | |
| unknown ns → petclinic (denied) | `curl petclinic-svc` from test-ns | ✗ Denied | |

```
# Paste actual curl outputs here:
PASTE HERE
```

---

## Module 6 — Tetragon

### Tetragon installed
```
# Paste: kubectl get pods -n kube-system -l app.kubernetes.io/name=tetragon
PASTE HERE
```

### TracingPolicy applied
```
# Paste: kubectl get tracingpolicies
PASTE HERE
```

### Sample events captured
```json
{
  "PASTE": "tetra getevents output here"
}
```

---

## Module 7 — AKS IaC

### Terraform plan output
```
# Paste: terraform plan
PASTE HERE
```

### AKS created (if Azure access available)
```
# Paste: az aks show --name aks-petclinic-prod -o table
PASTE HERE
```

---

## Module 8 — CI/CD

### GitHub Actions run
```
# Link to GitHub Actions run:
# https://github.com/YOUR-USERNAME/spring-petclinic/actions/runs/XXXXX
```

### Helm release status
```
# Paste: helm status petclinic -n petclinic
PASTE HERE
```

### Pod health after deploy
```
# Paste: kubectl rollout status deployment/petclinic -n petclinic
PASTE HERE
```

---

## Module 9 — Runbook
See:
- `runbooks/rancher_to_aks_cutover_runbook.md`
- `runbooks/rollback_plan.md`
- `runbooks/hypercare_plan.md`
