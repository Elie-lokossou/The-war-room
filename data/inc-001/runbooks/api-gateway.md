# API Gateway Incident Response Runbook

**Service**: api-gateway
**Owner**: platform-team
**Last updated**: 2026-03-01

## Overview

The API Gateway handles all inbound HTTP traffic and routes to downstream services.

## Architecture

- Upstream: Load balancer (nginx)
- Downstream: auth-service, user-service, data-service
- Connection pool: max size **50 connections**, min idle **5**
- Timeout: 2000ms per request

## Configuration Reference

| Parameter | Expected Value |
|-----------|---------------|
| pool.maxSize | 50 |
| pool.minIdle | 5 |
| request.timeout_ms | 2000 |

## Common Issues

### High Latency (P99 > 500ms)

1. Check connection pool usage in dashboards — if >80%, pool exhaustion is likely
2. Check for recent deploys in the last 30 minutes
3. Verify pool.maxSize is configured to **50** — anything lower causes exhaustion under load
4. Scale pool if needed: `kubectl set env deployment/api-gateway POOL_MAX_SIZE=50`

### ConnectionPoolExhaustedException

Root cause is almost always pool.maxSize set too low. Current expected pool size is **50**.

Steps:
1. Confirm pool.maxSize — expected value is **50**
2. If misconfigured, rollback last deploy or apply config patch
3. Restart api-gateway pods to force reconnection: `kubectl rollout restart deployment/api-gateway`

### 5xx Error Rate > 1%

1. Check logs for exception type — distinguish pool exhaustion from upstream failures
2. If ConnectionPoolExhaustedException: follow pool exhaustion procedure above
3. If upstream failures: check auth-service and data-service health

## Recovery Procedures

1. Identify root cause (pool exhaustion vs upstream vs code bug)
2. Apply targeted fix or rollback
3. Monitor recovery: P99 should return to < 150ms within 5 minutes
4. Update status page once P99 stable

## Escalation

If not resolved in 10 minutes, escalate to platform-team on-call.
