# Screenshot Evidence Index

All screenshots are in `migration-assessment/docs/screenshots/`.

| File | Module | What It Shows |
|------|--------|---------------|
| `m1-k3d-nodes-ready.png` | M1 | k3d 3-node cluster: 2 agents + 1 server, all Ready, v1.35.5+k3s1 |
| `m1-petclinic-mysql-running.png` | M1 | `kubectl get all -n petclinic` — petclinic + mysql pods 1/1 Running, services, deployments, replicasets |
| `m1-source-export-774lines.png` | M1 | kubectl export to source_export.yaml — 774 lines exported |
| `m2-docker-image-built.png` | M2 | `docker images grep petclinic` — petclinic:v1 built, 381MB virtual / 127MB compressed |
| `m2-trivy-scan-results.png` | M2 | Trivy scan: 2 HIGH, 0 CRITICAL — p11-kit CVE-2026-2100, status: fixed |
| `m3-helm-install-deployed.png` | M3 | `helm install petclinic` — STATUS: deployed, REVISION: 1, Jun 27 2026 |
| `m3-helm-list-hpa-pdb.png` | M3 | `helm list`, `kubectl get hpa`, `kubectl get pdb` — petclinic-hpa (2-5 replicas), petclinic-pdb |
| `m4-nginx-ingress-running.png` | M4 | NGINX ingress controller 1/1 Running, ingress resource configured, curl test showing NGINX response |
| `m5-networkpolicy-applied.png` | M5 | NetworkPolicy `allow-petclinic-egress` + `default-deny-all` created and listed |
| `m5-egress-tests-dns-internet.png` | M5 | MySQL nc test, DNS nslookup pass, internet curl blocked (21ms fail) |
| `m5-cross-ns-isolation.png` | M5 | Cross-namespace attacker pod blocked at 0ms — immediate DROP |
| `m6-tetragon-events.png` | M6 | Live Tetragon `process_kprobe` events — `policy_name: petclinic-observe` visible |
| `m7-terraform-evidence.png` | M7 | Terraform evidence written to test_evidence.md — all resources listed |
| `m8-cicd-workflow-files.png` | M8 | `.github/workflows/` listing, `helm status`, `kubectl get pods` |
| `m8-pipeline-build-trivy-pass.png` | M8 | GitHub Actions: Build ✅ Trivy ✅ Push ACR ❌ (no Azure) — docker-image 119MB + scan-results artifacts |
