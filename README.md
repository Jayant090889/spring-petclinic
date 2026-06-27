# Rancher to AKS Migration Assessment
### Spring PetClinic — Kubernetes Engineer Assessment Submission
**Candidate:** Jayant Prateek | AVP Cloud & DevOps Engineer | OCBC Bank, Singapore

---

## Assessment Summary

This repository demonstrates end-to-end migration of the Spring PetClinic
monolith from a Rancher-managed Kubernetes environment (simulated via k3d)
to Azure Kubernetes Service (AKS), including:

- Workload discovery and dependency inventory (Python crawler)
- Container hardening (multi-stage Dockerfile, non-root, Trivy scan)
- Production-grade Kubernetes manifests and Helm chart (3 environment overlays)
- NGINX Ingress with TLS + HAProxy comparison design
- Cilium network policies with egress test matrix evidence
- Tetragon runtime observability (TracingPolicy + operational design)
- AKS target architecture via Terraform (Cilium CNI, Key Vault, workload identity)
- CI/CD pipeline via GitHub Actions (build → scan → push → deploy)
- Migration runbook, rollback plan, and 72-hour hypercare plan

---

## Repository Structure

```
migration-assessment/
├── discovery/          # Module 1 — inventory crawler + outputs
├── docker/             # Module 2 — Dockerfile + docker-compose
├── kubernetes/         # Module 3/4/5 — manifests (base, ingress, network, security, hpa-pdb)
├── helm/petclinic/     # Module 3 — Helm chart with 3 environment overlays
├── cicd/               # Module 8 — GitHub Actions pipeline
├── iac/                # Module 7 — Terraform for AKS
├── runbooks/           # Module 9 — cutover, rollback, hypercare
└── docs/               # Architecture, decisions, evidence, risks
```

## Quick Start — Run Locally

```bash
# 1. Clone this repo
git clone https://github.com/YOUR-USERNAME/spring-petclinic
cd spring-petclinic

# 2. Start source cluster (Rancher simulation)
k3d cluster create rancher-source --agents 2 --port "8080:80@loadbalancer"

# 3. Deploy PetClinic + MySQL on source
helm install petclinic migration-assessment/helm/petclinic \
  -f migration-assessment/helm/petclinic/values.onprem.yaml \
  --namespace petclinic --create-namespace

# 4. Run inventory crawler
kubectl get all,configmaps,secrets,ingress,pvc,serviceaccounts,networkpolicies \
  -A -o yaml > migration-assessment/discovery/source_export.yaml
python3 migration-assessment/discovery/k8s_inventory_crawler.py \
  --input migration-assessment/discovery/source_export.yaml \
  --output migration-assessment/discovery/

# 5. See test evidence
cat migration-assessment/docs/test_evidence.md
```

## Candidate Notes
- 14+ years cloud & DevOps experience across OCBC Bank, JP Morgan, DBS Bank
- HashiCorp Terraform Associate certified
- AWS Solutions Architect + SysOps certified
- Real-world banking migration experience at AVP level in Singapore
