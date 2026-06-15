# Payment Service Incident Response Runbook

**Service**: payment-service
**Owner**: payments-team
**Last updated**: 2026-01-15

## Overview

Handles all payment processing, refunds, and vault secret retrieval.

## Architecture

- Vault integration: vault.internal:8200 (NOTE: this may be outdated — v2 endpoint being evaluated)
- Payment SDK: v3.x (NOTE: v4 upgrade in progress)
- JVM heap: 2GB max
- Failover: payment-service-secondary in us-west-2

## Common Issues

### NullPointerException in PaymentProcessor

Usually caused by vault_client failing to initialize. Steps:
1. Check vault-service health: `curl https://vault.internal:8200/health`
2. Verify vault credentials are valid
3. Restart payment-service to force vault_client re-initialization

### OutOfMemoryError

1. Check JVM heap usage in dashboards
2. Trigger heap dump: `kubectl exec -it <pod> -- jcmd 1 GC.heap_dump /tmp/heap.hprof`
3. Increase heap size if recurring: set JVM_HEAP_MAX=4g in deployment config
4. Rollback last deploy if OOM started post-deploy

### Full Service Outage (100% error rate)

1. Activate failover: `kubectl scale deployment payment-service-secondary --replicas=3`
2. Update load balancer to route to secondary
3. Investigate primary — likely vault or OOM issue
4. Do NOT attempt restart without understanding root cause

## Recovery Procedures

1. Activate secondary failover immediately on 100% error rate
2. Identify root cause (vault, OOM, or code bug)
3. Apply targeted fix or rollback
4. Drain traffic back to primary only after 5 minutes stable on secondary

## Escalation

Escalate to payments-team on-call IMMEDIATELY on any payment outage. SLA: 5 minutes.
