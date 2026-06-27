# AKS Target Architecture — Rancher to AKS Migration

> **Candidate note:** This architecture reflects my experience designing secure cloud landing zones at OCBC Bank (AVP Cloud Engineering), where I managed Azure and AWS environments for production banking workloads under MAS Technology Risk Management (TRM) guidelines. All design decisions below are grounded in real banking production experience, not theoretical patterns.


## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  AZURE (southeastasia region)                                       │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Resource Group: rg-petclinic-migration                      │   │
│  │                                                              │   │
│  │  ┌─────────────┐   ┌──────────────────────────────────────┐ │   │
│  │  │ Azure ACR   │   │  AKS Cluster: aks-petclinic-prod     │ │   │
│  │  │ (image reg) │   │                                      │ │   │
│  │  └──────┬──────┘   │  ┌──────────────┐ ┌──────────────┐  │ │   │
│  │         │ AcrPull  │  │ System Pool  │ │ User Pool    │  │ │   │
│  │         └──────────┼──│ (kube-system)│ │ 2-5 nodes    │  │ │   │
│  │                    │  └──────────────┘ │ D4s_v3       │  │ │   │
│  │  ┌─────────────┐   │                  │              │  │ │   │
│  │  │ Key Vault   │   │  ┌────────────────────────────┐ │  │ │   │
│  │  │ (secrets)   │◄──┼──│ Namespace: petclinic       │ │  │ │   │
│  │  └─────────────┘   │  │                            │ │  │ │   │
│  │                    │  │  [NGINX Ingress]            │ │  │ │   │
│  │  ┌─────────────┐   │  │       ↓                    │ │  │ │   │
│  │  │ Azure DB    │◄──┼──│  [petclinic pods x2]       │ │  │ │   │
│  │  │ for MySQL   │   │  │       ↓                    │ │  │ │   │
│  │  └─────────────┘   │  │  [CiliumNetworkPolicy]     │ │  │ │   │
│  │                    │  └────────────────────────────┘ │  │ │   │
│  │  ┌─────────────┐   │                                  │  │ │   │
│  │  │ Log Analytics│  │  Azure CNI powered by Cilium     │  │ │   │
│  │  │ + Monitor   │◄──│  Managed NAT Gateway (egress)    │  │ │   │
│  │  └─────────────┘   └──────────────────────────────────┘  │ │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Source vs Target Component Mapping

| Source (Rancher / k3d) | Target (AKS) | Migration Pattern |
|------------------------|--------------|------------------|
| k3d/Rancher cluster | AKS aks-petclinic-prod | Replatform |
| Docker local image | Azure Container Registry | Replatform |
| Kubernetes Secret | Azure Key Vault + CSI Driver | Replatform |
| NGINX Ingress (self-managed) | NGINX Ingress via Helm on AKS | Rehost |
| HAProxy edge gateway | Documented for comparison — not migrated | Retire |
| Local MySQL container | Azure Database for MySQL Flexible Server | Replatform |
| Manual kubectl deploy | GitHub Actions + Helm + ArgoCD | Refactor |
| No network policy | CiliumNetworkPolicy (default deny) | Refactor |
| No runtime monitoring | Tetragon eBPF observability | Add |

## AKS Cluster Design Decisions

### Networking: Azure CNI powered by Cilium
- Enables CiliumNetworkPolicy for FQDN-based egress control
- Required for partner API allowlisting in banking context
- overlay mode reduces IP address consumption

### Egress: Managed NAT Gateway
- Fixed outbound IP for partner bank API allowlists
- Required by MAS TRM for auditable network egress
- Alternative: userDefinedRouting via Azure Firewall for stricter control

### Security: Workload Identity
- Replaces service principal with managed identity
- Pods authenticate to Azure Key Vault using OIDC token
- No long-lived credentials stored in cluster

---

## AKS Operational Governance

### Namespace Governance
| Namespace | Purpose | Resource Quota | Who Can Deploy |
|-----------|---------|---------------|----------------|
| petclinic | Application workloads | CPU: 4 cores, Memory: 8Gi | Platform Team via GitHub Actions only |
| ingress-nginx | Ingress controller | CPU: 1 core, Memory: 2Gi | Platform Team only |
| monitoring | Prometheus/Grafana | CPU: 2 cores, Memory: 4Gi | Platform Team only |
| kube-system | System components | No quota (system reserved) | AKS managed |

### Resource Quota (petclinic namespace)
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: petclinic-quota
  namespace: petclinic
spec:
  hard:
    requests.cpu: "2"
    requests.memory: 4Gi
    limits.cpu: "4"
    limits.memory: 8Gi
    count/pods: "10"
    count/services: "5"
    persistentvolumeclaims: "2"
```

### Subnet Sizing
| Subnet | CIDR | Purpose | Nodes/IPs |
|--------|------|---------|-----------|
| aks-system-subnet | 10.1.0.0/24 | System node pool | 256 IPs — supports up to ~85 pods |
| aks-user-subnet | 10.1.1.0/23 | User node pool (autoscale 2–5) | 512 IPs — headroom for scale |
| aks-pod-subnet | 10.2.0.0/16 | Pod CIDR (overlay mode) | 65,536 pod IPs |
| private-endpoint-subnet | 10.1.4.0/28 | Private endpoints (MySQL, Key Vault) | 16 IPs sufficient |

### Private vs Public Endpoint Decision
- **AKS API server**: Public endpoint with authorized IP ranges (MAS TRM: restrict to corporate IP + CI/CD runner IPs)
- **ACR**: Private endpoint in aks-user-subnet — no public pull from internet
- **Azure Database for MySQL**: Private endpoint only — no public access
- **Azure Key Vault**: Private endpoint — accessed via CSI driver from pod identity
- **AKS Ingress**: Public IP (LoadBalancer) — exposed internet-facing via NGINX ingress

### AKS Backup and Restore Strategy
| Component | Tool | RPO | RTO | Notes |
|-----------|------|-----|-----|-------|
| Kubernetes manifests | GitHub (GitOps) | Near-zero | <10 min | Helm chart in repo — redeploy from Git |
| Application state | Stateless | N/A | N/A | No state in pods |
| MySQL data | Azure Database automated backup | 7 days | <1 hour | Point-in-time restore built into Azure DB |
| Secrets | Azure Key Vault soft-delete | 90 days | Minutes | Versioned, recoverable |
| AKS cluster config | Terraform state | On-demand | 10 min | terraform apply recreates cluster |
| Container images | ACR geo-replication | Real-time | Minutes | Images replicated across regions |

### RBAC Boundaries
| Role | Scope | Who | What they can do |
|------|-------|-----|-----------------|
| cluster-admin | Cluster | Platform Lead only | Full cluster access |
| namespace-editor | petclinic namespace | CI/CD service account | Deploy and manage workloads |
| namespace-viewer | petclinic namespace | Dev team | Read-only: logs, pod status |
| AKS RBAC Admin | Azure RBAC | Security Team | Manage cluster RBAC assignments |
