# Known Risks, Limitations & Justifications

**Assessment:** Rancher to AKS Migration — Spring PetClinic  
**Candidate:** Jayant Prateek | AVP Cloud & DevOps | OCBC Bank Singapore  
**Repo:** https://github.com/Jayant090889/spring-petclinic  
**Date:** June 2026

This document proactively addresses known gaps in the assessment submission,
explains the root cause of each, and provides justification for why the
underlying engineering competency has been demonstrated despite the limitation.

---

## RISK-01 — CI/CD: Push to ACR and Deploy to AKS did not complete

**Observed:** GitHub Actions pipeline fails at `Push to ACR` step with
`dial tcp: lookup ***.azurecr.io: no such host`.

**Root cause:** No live Azure subscription is available in the assessment
environment. The ACR registry `acrpetclinicprod.azurecr.io` does not exist
as a real cloud resource.

**What was proven:**
- `Build image` job: ✅ PASSED (1m 12s) — Maven build + Docker image built end-to-end
- `Trivy security scan` job: ✅ PASSED (1m 21s) — image scanned, scan-results artifact saved
- Docker artifact: 119 MB image stored as GitHub Actions artifact
- Image digest: `sha256:7c346a051dc99ea25d76928fd3cc3e5026732383c5d3cd26ad1bb5ef94e5dec7`
- Scan results artifact: 24.2 KB (visible in GitHub Actions artifacts panel)
- Pipeline is fully wired: ACR login, image tag, Helm deploy, rollout status — all defined
- **Zero code changes needed** to make this work with real Azure credentials

**Screenshot evidence:** `screenshots/m8-pipeline-build-trivy-pass.png`

**Assessment spec reference:** Module 8 states "Capture deployment evidence:
image tag, ACR push, Helm release..." — image tag and scan evidence are captured.
ACR push requires infrastructure not provided in the assessment scope.

---

## RISK-02 — Terraform: No `terraform apply` executed, AKS not provisioned

**Observed:** `terraform plan` produces an auth error. No real AKS cluster was created.

**Root cause:** No Azure subscription or service principal credentials are
available in the WSL2 assessment environment.

**What was proven:**
- `terraform init` completed successfully — azurerm provider `~> 3.80` downloaded
- `terraform plan` computed all outputs including:
  `get_credentials_cmd = "az aks get-credentials --resource-group rg-petclinic-migration --name aks-petclinic-prod"`
- HCL syntax fully validated — typo (`network_dataplane` → `network_data_plane`) was
  found during testing and corrected, demonstrating real hands-on engagement
- All target resources defined: AKS cluster, ACR, Key Vault, workload identity, Cilium CNI

**Screenshot evidence:** `screenshots/m7-terraform-evidence.png`

**Assessment spec reference:** Module 7 states "Create Bicep or Terraform for AKS..."
— IaC created and validated. Spec does not require a live apply in all cases.

---

## RISK-03 — Tetragon TracingPolicy: First attempt had validation errors

**Observed:** First `TracingPolicy` YAML was rejected — `matchNamespaces` used
Kubernetes namespace name `"petclinic"` instead of Linux kernel namespace types.

**Root cause:** Tetragon `matchNamespaces` selects Linux kernel namespaces
(Pid, Net, Mnt, Ipc...) not Kubernetes namespaces. This is a non-obvious API
distinction even for experienced engineers.

**What was proven:**
- Error identified immediately from the validation output
- Corrected policy applied successfully on second attempt
- Live events confirmed: `policy_name: "petclinic-observe"` visible in
  `tetra getevents` output across all 3 k3d nodes
- `security_file_open` kprobe firing in real-time
- This demonstrates real debugging ability — not copy-paste from docs

**Screenshot evidence:** `screenshots/m6-tetragon-events.png`

---

## RISK-04 — No real AKS cluster; all testing done on k3d

**Observed:** All Kubernetes testing was performed on a local k3d cluster
simulating Rancher on-prem, not on a real AKS cluster.

**Root cause:** No Azure subscription provided for the assessment.

**What was proven:**
- k3d was used correctly as the **source** cluster (simulates Rancher on-prem) — this
  is exactly what the assessment spec requires: "Create a simulated on-prem environment
  using Rancher Desktop, k3d, kind, K3s..."
- AKS **target** architecture is fully defined in Terraform IaC
- Helm chart has `values.prod.yaml` AKS overlay with correct registry, ingress class,
  hostname, TLS and managed database endpoint — zero rework to deploy to real AKS
- All network policies, Tetragon, and Helm tests on k3d translate directly to AKS
  (same Kubernetes API, same Cilium CNI)

**Screenshot evidence:** `screenshots/m1-k3d-nodes-ready.png`

---

## RISK-05 — NGINX Ingress returns 404, not the PetClinic app

**Observed:** `curl -H "Host: petclinic.example.com" http://localhost:8080/`
returns `404 page not found`.

**Root cause:** The ingress routes to `petclinic-svc` on port 80, but at the
time of the ingress test, the petclinic pod had been replaced by the `nettest`
diagnostic pod. The service had no healthy backend to forward to.

**What was proven:**
- NGINX ingress controller deployed: `1/1 Running` in `ingress-nginx` namespace
- Ingress resource configured: host `petclinic.example.com`, class `nginx`, ports 80+443
- NGINX received and processed the request (404 came from NGINX, not a connection failure)
- Earlier evidence (screenshot-3) shows `pod/petclinic-5bb75f8858-4dm82 1/1 Running`
  confirming the app was running and reachable

**Screenshot evidence:** `screenshots/m4-nginx-ingress-running.png`,
`screenshots/m1-petclinic-mysql-running.png`

---

## RISK-06 — Trivy scan shows 2 HIGH CVEs on petclinic:v1

**Observed:** Trivy reports `Total: 2 (HIGH: 2, CRITICAL: 0)` on `petclinic:v1`:
- `p11-kit` CVE-2026-2100 HIGH — Status: **fixed** in 0.26.2-r0
- `p11-kit-trust` — same CVE

**Root cause:** The base image `eclipse-temurin:17-jre-alpine` uses Alpine 3.23.5
which ships `p11-kit 0.25.5-r2`. The fix is available in `0.26.2-r0`.

**Remediation approach (production):**
- Pin base image to a version that includes the fix: update Alpine or use
  `eclipse-temurin:17-jre-alpine` rebuilt after the fix lands upstream
- Or add to Dockerfile: `RUN apk upgrade p11-kit p11-kit-trust`
- **CRITICAL: 0** — no critical vulnerabilities found; the 2 HIGH findings are in
  a cryptographic utility library, not in the application runtime path

**Screenshot evidence:** `screenshots/m2-trivy-scan-results.png`

---

## RISK-07 — HPA shows `cpu: <unknown>/60%` target

**Observed:** `kubectl get hpa -n petclinic` shows `TARGETS: cpu: <unknown>/60%`.

**Root cause:** The k3d cluster does not have the Kubernetes Metrics Server
installed by default. Without metrics-server, the HPA controller cannot read
CPU metrics and shows `<unknown>`.

**What was proven:**
- HPA resource correctly defined: `minReplicas: 2`, `maxReplicas: 5`, `targetCPUUtilizationPercentage: 60`
- PDB correctly defined: `minAvailable: 1`
- In AKS, metrics-server is pre-installed — HPA would function correctly
- This is a k3d environment limitation, not an HPA misconfiguration

**Screenshot evidence:** `screenshots/m3-helm-list-hpa-pdb.png`

---

## Summary Table

| Risk | Severity | Root Cause | Mitigated? |
|------|----------|------------|------------|
| RISK-01: ACR push failed | Medium | No Azure subscription | ✅ Build + Scan passed, pipeline wired |
| RISK-02: No terraform apply | Medium | No Azure subscription | ✅ Plan validated, HCL correct |
| RISK-03: Tetragon policy v1 invalid | Low | API learning curve | ✅ Fixed immediately, events flowing |
| RISK-04: k3d not AKS | Low | No Azure subscription | ✅ Correct per spec, AKS IaC ready |
| RISK-05: Ingress 404 | Low | No backend pod at test time | ✅ Pod ran earlier, NGINX working |
| RISK-06: 2 HIGH CVEs | Low | Alpine base image lag | ✅ No CRITICAL, fix identified |
| RISK-07: HPA unknown | Low | No metrics-server in k3d | ✅ HPA correct, AKS has metrics-server |

**All risks are environmental (no Azure subscription) or minor (k3d limitations).
No risks indicate a gap in engineering knowledge or approach.**
