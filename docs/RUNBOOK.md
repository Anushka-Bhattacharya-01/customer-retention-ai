# Runbook – Customer Retention AI API

Service: `churn-api` (FastAPI) in namespace `ml-serving` on Amazon EKS.
Dependencies: churn ML model (S3), Amazon Bedrock (LLM), Postgres (conversations and usage).

## Quick checks

```bash
kubectl get pods -n ml-serving -l app.kubernetes.io/name=churn-api
kubectl logs -n ml-serving deploy/churn-churn-api --tail=100
kubectl describe pod -n ml-serving <pod>
kubectl get configmap churn-churn-api -n ml-serving -o yaml
curl http://<service>/health
curl http://<service>/assistant/usage
```

## 1. Pods in CrashLoopBackOff after deploy

| Check | Command | Likely cause → fix |
|---|---|---|
| Startup error in logs | `kubectl logs <pod> --previous` | `Model not found` → wrong `model.s3Uri` or model not uploaded; check `aws s3 ls s3://<bucket>/models/latest/` |
| S3 AccessDenied | logs | IRSA annotation missing or wrong role: `kubectl get sa churn-api -n ml-serving -o yaml` |
| Database connection error | logs | Secret `churn-api-db` missing or wrong `DATABASE_URL`: `kubectl get secret churn-api-db -n ml-serving` |

Rollback: `helm rollback churn -n ml-serving` (previous image and config).

## 2. `/assistant/ask` returns 502 (assistant errors)

1. Check the error rate: SQL query 3 in `sql/usage_queries.sql`, or the `assistant_requests_total{status="error"}` metric.
2. Read the failed answers (SQL query 4). Common messages:
   - `AccessDeniedException` → IRSA role lacks `bedrock:InvokeModel` for this model, or model access is not enabled in the Bedrock console for the region.
   - `ThrottlingException` → Bedrock quota reached; reduce traffic or request a quota increase.
   - `Stopped after 5 steps` → the LLM kept calling tools; review the prompt and tool descriptions.
3. Temporary mitigation: set `assistant.llmProvider=mock` and `helm upgrade` so `/predict` and the assistant keep responding while Bedrock is fixed.

## 3. LLM cost spike

1. `curl /assistant/usage` and Grafana `llm_cost_usd_total` rate.
2. SQL query 2: find the most expensive conversations.
3. Typical causes: very long questions, a loop of tool calls, or a more expensive model ID set in the ConfigMap.
4. Controls: `maxOutputTokens`, `maxAgentSteps`, question length limit (500 characters in the API).

## 4. High latency

1. `assistant_latency_seconds` histogram in Grafana, and `avg_latency_ms` from `/assistant/usage`.
2. If LLM latency is normal but the API is slow: check pod CPU (`kubectl top pods`) and HPA (`kubectl get hpa -n ml-serving`).

## Incident note template

```
Incident: <title>                Severity: <P1-P4>
Start / end (IST): <time> / <time>
Impact: <who was affected, how many requests failed>
Detection: <alert / user report>
Root cause: <one or two sentences>
Fix: <what was changed>
Follow-up tickets: <ticket IDs>
```
