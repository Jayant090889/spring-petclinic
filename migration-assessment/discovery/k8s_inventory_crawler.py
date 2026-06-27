#!/usr/bin/env python3
"""
k8s_inventory_crawler.py — ADDM-style Kubernetes workload inventory crawler
Rancher-to-AKS Migration Assessment
Author: Jayant Prateek

Usage:
    # Export cluster resources first:
    kubectl get all,configmaps,secrets,ingress,pvc,serviceaccounts,\
networkpolicies -A -o yaml > source_export.yaml

    # Run crawler:
    python3 k8s_inventory_crawler.py --input source_export.yaml
"""

import yaml
import json
import csv
import argparse
import sys
from pathlib import Path
from datetime import datetime

SKIP_NAMESPACES = {"kube-system", "kube-public", "kube-node-lease"}

DEPENDENCY_TYPES = {
    "database":       ["mysql", "postgres", "mongodb", "redis", "mssql", "db"],
    "message_queue":  ["kafka", "rabbitmq", "activemq", "nats", "queue"],
    "ingress":        ["ingress", "nginx", "haproxy", "traefik"],
    "secret":         ["secret", "password", "key", "token", "credential"],
    "external_api":   ["http", "https", "api", "url", "endpoint"],
    "filesystem":     ["pvc", "volume", "mount", "nfs", "ceph"],
}

def classify_dependency(value: str) -> str:
    val = str(value).lower()
    for dep_type, keywords in DEPENDENCY_TYPES.items():
        if any(k in val for k in keywords):
            return dep_type
    return "unknown"

def extract_containers(spec: dict) -> list:
    containers = []
    template = spec.get("template", {})
    pod_spec  = template.get("spec", spec) if template else spec
    for c in pod_spec.get("containers", []) + pod_spec.get("initContainers", []):
        containers.append({
            "name":    c.get("name"),
            "image":   c.get("image", "unknown"),
            "ports":   [p.get("containerPort") for p in c.get("ports", [])],
            "env":     [e.get("name") for e in c.get("env", [])],
            "secrets": [e.get("valueFrom", {}).get("secretKeyRef", {}).get("name")
                        for e in c.get("env", [])
                        if e.get("valueFrom", {}).get("secretKeyRef")],
        })
    return containers

def crawl(input_file: str, output_dir: str = "."):
    print(f"[*] Reading: {input_file}")
    with open(input_file) as f:
        docs = list(yaml.safe_load_all(f))

    docs = [d for d in docs if d and isinstance(d, dict) and "kind" in d]
    print(f"[*] Parsed {len(docs)} Kubernetes resources")

    inventory    = []
    dependencies = []
    network_flows = []

    for doc in docs:
        meta      = doc.get("metadata", {})
        namespace = meta.get("namespace", "default")
        name      = meta.get("name", "unknown")
        kind      = doc.get("kind", "Unknown")

        if namespace in SKIP_NAMESPACES:
            continue

        spec = doc.get("spec", {})
        containers = extract_containers(spec)

        item = {
            "name":        name,
            "namespace":   namespace,
            "kind":        kind,
            "images":      [c["image"] for c in containers],
            "ports":       [p for c in containers for p in c["ports"] if p],
            "env_vars":    [e for c in containers for e in c["env"]],
            "secrets":     list(set(s for c in containers for s in c["secrets"] if s)),
            "labels":      meta.get("labels", {}),
            "annotations": meta.get("annotations", {}),
            "replicas":    spec.get("replicas", 1),
            "migration_pattern": classify_migration_pattern(kind, spec),
            "migration_risk":    assess_migration_risk(doc),
        }
        inventory.append(item)

        # Extract dependencies
        for env in item["env_vars"]:
            dep_type = classify_dependency(env)
            if dep_type != "unknown":
                dependencies.append({
                    "source_workload": name,
                    "source_namespace": namespace,
                    "dependency_type": dep_type,
                    "dependency_name": env,
                    "migration_action": recommend_migration_action(dep_type),
                })

        # Network flows from ingress rules
        if kind == "Ingress":
            for rule in spec.get("rules", []):
                host = rule.get("host", "*")
                for path in rule.get("http", {}).get("paths", []):
                    svc = path.get("backend", {}).get("service", {})
                    network_flows.append({
                        "flow_type":   "ingress",
                        "source":      f"external:{host}",
                        "destination": f"{namespace}/{svc.get('name', 'unknown')}",
                        "port":        svc.get("port", {}).get("number", ""),
                        "protocol":    "HTTPS/HTTP",
                        "policy":      "Allow",
                        "notes":       f"path: {path.get('path', '/')}",
                    })

    # Write JSON
    json_path = Path(output_dir) / "workload_inventory.json"
    with open(json_path, "w") as f:
        json.dump({"generated_at": datetime.utcnow().isoformat(),
                   "total_workloads": len(inventory),
                   "workloads": inventory}, f, indent=2, default=str)

    # Write CSV
    csv_path = Path(output_dir) / "workload_inventory.csv"
    if inventory:
        with open(csv_path, "w", newline="") as f:
            fields = ["name", "namespace", "kind", "images", "ports",
                      "replicas", "migration_pattern", "migration_risk"]
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for item in inventory:
                row = {k: str(v) for k, v in item.items() if k in fields}
                w.writerow(row)

    # Write network flows CSV
    flows_path = Path(output_dir) / "network_flows.csv"
    if network_flows:
        with open(flows_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=network_flows[0].keys())
            w.writeheader()
            w.writerows(network_flows)

    # Write dependency summary markdown
    dep_path = Path(output_dir) / "dependency_summary.md"
    write_dependency_summary(dep_path, inventory, dependencies)

    print(f"[✓] workload_inventory.json  — {len(inventory)} workloads")
    print(f"[✓] workload_inventory.csv")
    print(f"[✓] network_flows.csv        — {len(network_flows)} flows")
    print(f"[✓] dependency_summary.md")

    # Print migration summary
    risks = [i["migration_risk"] for i in inventory]
    print(f"\n Migration Risk Summary:")
    for level in ["HIGH", "MEDIUM", "LOW"]:
        count = risks.count(level)
        print(f"  {level}: {count} workloads")

    return inventory


def classify_migration_pattern(kind: str, spec: dict) -> str:
    """Classify workload into rehost/replatform/refactor/retire."""
    if kind in ["Job", "CronJob"]:
        return "replatform"
    if kind == "StatefulSet":
        return "replatform"   # stateful requires PV migration
    if kind == "DaemonSet":
        return "refactor"     # may not translate to AKS node topology
    return "rehost"           # stateless deployments = direct lift-and-shift


def assess_migration_risk(doc: dict) -> str:
    """Assess migration risk based on workload characteristics."""
    spec = doc.get("spec", {})
    kind = doc.get("kind", "")
    risk_score = 0

    if kind == "StatefulSet":           risk_score += 3
    if kind == "DaemonSet":             risk_score += 2
    if spec.get("volumes"):             risk_score += 2
    if doc.get("metadata", {}).get("annotations", {}).get(
            "kubectl.kubernetes.io/last-applied-configuration"): risk_score += 1

    if risk_score >= 4:
        return "HIGH"
    elif risk_score >= 2:
        return "MEDIUM"
    return "LOW"


def recommend_migration_action(dep_type: str) -> str:
    actions = {
        "database":      "Migrate to Azure Database for MySQL/PostgreSQL; update connection strings in AKS Secret",
        "message_queue": "Deploy RabbitMQ/Kafka on AKS or use Azure Service Bus",
        "secret":        "Migrate to Azure Key Vault via Secret Store CSI Driver",
        "external_api":  "Verify FQDN reachable from AKS; add to CiliumNetworkPolicy toFQDNs",
        "filesystem":    "Map PVCs to Azure Disk or Azure Files CSI driver",
        "ingress":       "Replace with NGINX IngressClass on AKS",
    }
    return actions.get(dep_type, "Review and document")


def write_dependency_summary(path: Path, inventory: list, dependencies: list):
    with open(path, "w") as f:
        f.write("# Dependency Summary — Rancher to AKS Migration\n\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()} UTC\n\n")
        f.write(f"## Overview\n\n")
        f.write(f"| Metric | Count |\n|--------|-------|\n")
        f.write(f"| Total workloads | {len(inventory)} |\n")
        f.write(f"| Total dependencies | {len(dependencies)} |\n")
        dep_types = {}
        for d in dependencies:
            dep_types[d["dependency_type"]] = dep_types.get(d["dependency_type"], 0) + 1
        for t, c in dep_types.items():
            f.write(f"| {t.replace('_',' ').title()} dependencies | {c} |\n")

        f.write(f"\n## Workload Inventory\n\n")
        f.write("| Name | Namespace | Kind | Pattern | Risk |\n")
        f.write("|------|-----------|------|---------|------|\n")
        for item in inventory:
            f.write(f"| {item['name']} | {item['namespace']} | {item['kind']} "
                    f"| {item['migration_pattern']} | {item['migration_risk']} |\n")

        f.write(f"\n## Migration Wave Plan\n\n")
        f.write("| Wave | Criteria | Workloads | Target Window |\n")
        f.write("|------|----------|-----------|---------------|\n")
        f.write("| Wave 1 | Stateless, LOW risk, no PVC | Deployments with no volumes | Week 1 |\n")
        f.write("| Wave 2 | Stateful, MEDIUM risk, databases | StatefulSets, DB-dependent apps | Week 2 |\n")
        f.write("| Wave 3 | Ingress cutover, DNS switch | All ingress + DNS migration | Week 3 |\n")

        f.write(f"\n## Dependency Details\n\n")
        for dep_type in set(d["dependency_type"] for d in dependencies):
            f.write(f"\n### {dep_type.replace('_',' ').title()}\n\n")
            f.write("| Workload | Dependency | Migration Action |\n")
            f.write("|----------|------------|------------------|\n")
            for d in dependencies:
                if d["dependency_type"] == dep_type:
                    f.write(f"| {d['source_workload']} | {d['dependency_name']} "
                            f"| {d['migration_action']} |\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="K8s Inventory Crawler")
    parser.add_argument("--input",  default="source_export.yaml", help="Input YAML file")
    parser.add_argument("--output", default=".",                   help="Output directory")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"[!] Input file not found: {args.input}")
        print("[*] Run this first:")
        print("    kubectl get all,configmaps,secrets,ingress,pvc,serviceaccounts,networkpolicies -A -o yaml > source_export.yaml")
        sys.exit(1)

    crawl(args.input, args.output)
