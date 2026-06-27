# Dependency Summary — Rancher to AKS Migration

Generated: 2026-06-27T02:19:32.436509 UTC

## Overview

| Metric | Count |
|--------|-------|
| Total workloads | 1 |
| Total dependencies | 0 |

## Workload Inventory

| Name | Namespace | Kind | Pattern | Risk |
|------|-----------|------|---------|------|
| unknown | default | List | rehost | LOW |

## Migration Wave Plan

| Wave | Criteria | Workloads | Target Window |
|------|----------|-----------|---------------|
| Wave 1 | Stateless, LOW risk, no PVC | Deployments with no volumes | Week 1 |
| Wave 2 | Stateful, MEDIUM risk, databases | StatefulSets, DB-dependent apps | Week 2 |
| Wave 3 | Ingress cutover, DNS switch | All ingress + DNS migration | Week 3 |

## Dependency Details

