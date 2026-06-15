# User Service Incident Response Runbook

**Service**: user-service
**Owner**: backend-team
**Last updated**: 2026-05-10

## Overview

The User Service handles user authentication, profile retrieval, and order history.

## Architecture

- Database: PostgreSQL (primary + 2 read replicas)
- Connection pool: max size **20 connections**
- Query timeout: 100ms warning, 500ms error threshold

## Common Issues

### Slow Query Spikes

Often caused by missing indexes or table growth. Steps:
1. Check EXPLAIN ANALYZE on slow queries from logs
2. Verify no index degradation (autovacuum may be running)
3. Check database CPU and I/O — may be transient
4. Usually self-resolves within 5–10 minutes

### High CPU

1. Check for N+1 query patterns in recent code changes
2. Check for missing indexes on frequently queried columns
3. Escalate to DBA team if sustained > 15 minutes

## Recovery Procedures

1. If transient (< 10 min): monitor, document, close
2. If sustained: identify slow query pattern, add index or optimize query
3. If correlated with deploy: rollback and investigate

## Escalation

Escalate to backend-team on-call if not self-resolved in 10 minutes.
