# AI-Powered HR System - Blueprint Reference

This document summarizes the product vision. Implementation status is tracked in the root README.

## Core Layers

1. **Candidate Acquisition** - job boards, applications, sourcing
2. **Recruitment Intelligence** - parsing, matching, ranking, assessments, JD generation
3. **HR Operations** - onboarding, attendance, leave, burnout risk, payroll, compliance tracking
4. **Employee Intelligence** - performance, engagement, workforce planning, wellness signals
5. **AI Decision Layer** - predictions, recommendations, copilot, explainable scoring
6. **Communication** - chatbots, notifications, scheduling, interview alerts
7. **Security & Compliance** - RBAC, audit logs, privacy masking, GDPR

## Roadmap

| Phase | Scope |
| ----- | ----- |
| MVP | Parser, matching, chatbot, scheduling, analytics, onboarding, RAG |
| Growth | RBAC, audit logging, rate limiting, notification events, payroll, GraphQL/WebSocket adapters |
| Enterprise | Multi-tenant, compliance engine, agentic recruiters, OAuth/MFA, provider integrations, MLOps |

## Current Implementation Notes

- The repository implements the full service skeleton from the architecture diagram.
- Gateway security includes CORS, headers, rate limiting, audit logs, JWT auth, and role checks.
- HR operations include onboarding task plans, leave request submission, burnout risk prediction, salary profile management, payroll run automation, and interview scheduling.
- AI components include resume extraction, job description generation, semantic matching, explainable scoring, and RAG-assisted HR chat.
- Eventing is represented by notification records and WebSocket delivery hooks; Kafka/RabbitMQ/Redis Streams remain production options.
- Local development defaults to SQLite; Docker Compose includes PostgreSQL for production-like runs.
- Terraform, Airflow, and MLflow are represented as rollout boundaries under `infra/`.

See the full specification in the project requirements document provided at kickoff.
