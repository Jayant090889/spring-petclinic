# Migration Decisions — Rationale and Tradeoffs

> **Candidate note:** These decisions reflect actual choices I made during on-prem to cloud migrations at OCBC Bank and Globecast Asia, adapted for this assessment. Where I reference banking context, it is drawn from direct experience managing similar migrations in Singapore's regulated financial sector.


## Decision 1: Helm over Kustomize
**Chosen:** Helm
**Rationale:** Team has existing Helm expertise. Helm's templating with
values overlays cleanly separates on-prem, dev-AKS, and prod-AKS configurations.
Rolling back a bad deployment is one command: `helm rollback`.
**Tradeoff:** Helm templates are less readable than Kustomize patches.
Kustomize would be preferred for GitOps-only workflows.

## Decision 2: NGINX over HAProxy as primary AKS ingress
**Chosen:** NGINX Ingress Controller
**Rationale:** Native AKS Application Routing addon support. Annotation-driven
configuration that platform team already understands. Well-documented migration
path from on-premises HAProxy.
**Tradeoff:** HAProxy offers better TCP-level routing and performance at very
high throughput (>50k RPS). Retained as design reference for legacy workloads
requiring Layer 4 routing.

## Decision 3: Terraform over Bicep for IaC
**Chosen:** Terraform (HashiCorp)
**Rationale:** Team holds HashiCorp Terraform Associate certification. Existing
Terraform modules for AWS and Azure in use at OCBC Bank. Multi-cloud portability.
**Tradeoff:** Bicep is Azure-native and produces simpler ARM output. Would be
preferred for Azure-only shops without existing Terraform investment.

## Decision 4: Managed NAT Gateway over Azure Firewall for egress
**Chosen:** Managed NAT Gateway (`managedNATGateway` outbound type)
**Rationale:** Fixed public IP for partner bank API allowlisting. Simpler to
operate than Azure Firewall. Sufficient for this workload's egress requirements.
**Tradeoff:** Azure Firewall with `userDefinedRouting` provides FQDN-level
logging, threat intelligence, and TLS inspection. Would be the production
recommendation for a full banking estate with 50+ workloads.

## Decision 5: Workload Identity over Service Principal
**Chosen:** Workload Identity (OIDC-based)
**Rationale:** No long-lived credentials stored in cluster or Key Vault.
Aligns with MAS TRM zero-trust principles. Azure-managed rotation.
**Tradeoff:** Requires OIDC issuer enabled on AKS and application code changes
to use DefaultAzureCredential. Service principal is simpler for legacy apps.

## Decision 6: GitHub Actions over Azure DevOps
**Chosen:** GitHub Actions
**Rationale:** Source repository is on GitHub. No additional Azure DevOps
organisation setup required. Free tier provides 2,000 minutes/month.
Syntax similar to GitLab CI (existing team knowledge from OCBC).
**Tradeoff:** Azure DevOps provides deeper Azure integration, audit trails
required by some banking compliance frameworks. For production banking use,
Azure DevOps with audit logging would be the recommendation.

## Decision 7: CiliumNetworkPolicy over standard NetworkPolicy
**Chosen:** CiliumNetworkPolicy
**Rationale:** AKS with Azure CNI powered by Cilium supports FQDN-based
egress control via `toFQDNs`. Standard NetworkPolicy only supports IP-based
rules — impractical for partner APIs with dynamic IPs.
**Tradeoff:** CiliumNetworkPolicy is Cilium-specific and not portable to
non-Cilium clusters. Requires Cilium CNI on AKS.
