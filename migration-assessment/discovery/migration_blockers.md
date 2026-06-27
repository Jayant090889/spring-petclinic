# Migration Blockers — Spring PetClinic Rancher to AKS

| ID | Blocker | Severity | Owner | Remediation | Status |
|----|---------|----------|-------|------------|--------|
| B001 | MySQL is a StatefulSet with hostPath PVC — direct migration not possible | HIGH | DBA | Replace with Azure Database for MySQL Flexible Server. Run mysqldump on source, restore to Azure DB before cutover. | Open |
| B002 | Kubernetes Secrets store DB credentials in base64 only — not MAS TRM compliant | HIGH | Security Team | Migrate secrets to Azure Key Vault. Implement Secret Store CSI Driver on AKS. Update pod spec to use secretProviderClass. | Open |
| B003 | No existing CI/CD pipeline — deployments are manual kubectl apply | MEDIUM | DevOps | Build GitHub Actions pipeline before cutover. Validate pipeline deploys to AKS non-prod 48hr before cutover. | Open |
| B004 | No NetworkPolicy on source cluster — all pod-to-pod traffic is open | MEDIUM | Platform Team | Implement default-deny + CiliumNetworkPolicy on AKS. Test all egress flows in non-prod before cutover. | Open |
| B005 | Container image runs as root (original Dockerfile) | MEDIUM | Platform Team | Rebuild image with non-root USER 1001. Update Dockerfile (done in migration-assessment/docker/Dockerfile). Test application startup. | Resolved |
| B006 | No readiness/liveness probes on source Deployment | LOW | Platform Team | Add /actuator/health/readiness and /actuator/health/liveness probes (done in Helm chart). | Resolved |
| B007 | TLS certificate not yet provisioned for AKS ingress hostname | MEDIUM | Security Team | Provision TLS cert via cert-manager on AKS or import to Key Vault. Complete before cutover. | Open |
| B008 | DNS TTL currently 3600 seconds — slow failover on rollback | LOW | NetOps | Reduce DNS TTL to 60 seconds 48hr before cutover window. | Open |
