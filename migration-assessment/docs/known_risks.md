# Known Risks — Rancher to AKS Migration

| Risk ID | Description | Severity | Likelihood | Impact | Owner | Mitigation | Residual Risk |
|---------|-------------|----------|-----------|--------|-------|------------|---------------|
| R001 | Database connection string change causes app startup failure on AKS | HIGH | Medium | HIGH | Platform Lead | Test in non-prod 48hr before cutover. Validate with smoke test. | LOW after testing |
| R002 | DNS propagation delay extends cutover window beyond planned 60 seconds | MEDIUM | Low | MEDIUM | NetOps | Reduce TTL to 60s at T-2hr. Monitor with dig +trace during cutover. | LOW |
| R003 | Azure Key Vault CSI driver secret sync delay causes pod startup failure | HIGH | Low | HIGH | Security Lead | Pre-warm secrets in CSI driver 24hr before cutover. Verify sync with kubectl describe secretproviderclass. | LOW |
| R004 | CiliumNetworkPolicy blocks legitimate egress to partner API on first deployment | HIGH | Medium | HIGH | Engineer | Test all egress flows in non-prod with identical CiliumNetworkPolicy 48hr before cutover. | LOW after testing |
| R005 | AKS HPA scales down during low-traffic cutover window causing latency spike | MEDIUM | Low | MEDIUM | Engineer | Set HPA minReplicas=2 during cutover window. Scale up manually if needed. | LOW |
| R006 | Tetragon TracingPolicy generates too many events causing observability overhead | LOW | Low | LOW | Engineer | Scope TracingPolicy to petclinic namespace only. Rate-limit event export. | LOW |
| R007 | Azure Database for MySQL connection pool exhausted under traffic spike | HIGH | Low | HIGH | DBA | Set max_connections appropriately. Configure connection pool in app (HikariCP). Monitor pool metrics during hypercare. | MEDIUM — monitor |
| R008 | GitHub Actions pipeline fails on first production deploy due to ACR permissions | MEDIUM | Low | MEDIUM | DevOps | Run pipeline in dry-run mode against non-prod AKS 24hr before cutover. | LOW |
