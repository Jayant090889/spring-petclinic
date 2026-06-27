# Smoke Test Checklist — Post-Migration Validation

## Application Smoke Tests (run immediately after DNS cutover)

| # | Test | Command | Pass Criteria | Owner |
|---|------|---------|--------------|-------|
| 1 | Health endpoint | `curl -sf https://petclinic.example.com/actuator/health` | Returns `{"status":"UP"}` | Engineer |
| 2 | Home page loads | `curl -sf https://petclinic.example.com/` | HTTP 200, contains "PetClinic" | QA |
| 3 | List owners | `curl -sf https://petclinic.example.com/owners` | HTTP 200, JSON or HTML list | QA |
| 4 | DB read | `curl -sf https://petclinic.example.com/owners/1` | HTTP 200, owner data returned | QA |
| 5 | DB write | Create new owner via UI or API | Record persists after page refresh | Business |
| 6 | TLS certificate | `curl -vI https://petclinic.example.com 2>&1 \| grep "SSL certificate verify ok"` | Cert valid, not self-signed warning | Engineer |

## Infrastructure Smoke Tests

| # | Test | Command | Pass Criteria |
|---|------|---------|--------------|
| 7 | Pods running | `kubectl get pods -n petclinic` | All pods `Running`, 0 `CrashLoopBackOff` |
| 8 | Correct replica count | `kubectl get deployment petclinic -n petclinic` | READY shows 2/2 |
| 9 | HPA active | `kubectl get hpa -n petclinic` | Shows current/target CPU |
| 10 | Ingress resolves | `kubectl get ingress -n petclinic` | EXTERNAL-IP populated |
| 11 | DB connection | `kubectl exec deploy/petclinic -n petclinic -- nc -zv $MYSQL_HOST 3306` | `Connection succeeded` |
| 12 | No restarts | `kubectl get pods -n petclinic` | RESTARTS column = 0 |

## Performance Validation (T+30 minutes)

```bash
# Install k6 if not already installed: brew install k6
k6 run --vus 50 --duration 2m - << 'K6SCRIPT'
import http from 'k6/http';
import { check } from 'k6';

export default function () {
  const res = http.get('https://petclinic.example.com/actuator/health');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
}
K6SCRIPT
```

**Pass criteria:** p95 response time < 500ms, error rate < 1%, no HTTP 5xx responses

## Business Validation

- [ ] Application team lead confirms: create, read, update, delete operations working
- [ ] Login/session flow working (if applicable)
- [ ] Email notifications working (if applicable)
- [ ] No data loss from pre-cutover state
- [ ] Business sign-off obtained and recorded in ServiceNow
