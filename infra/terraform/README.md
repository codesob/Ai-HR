# Terraform

This folder is the deployment boundary for the full architecture shown in the system diagram.

Expected production modules:

- VPC/networking
- Kubernetes cluster
- PostgreSQL
- Redis
- Qdrant or managed vector database
- S3-compatible object storage
- Secret manager
- CI/CD service account

The MVP runs with Docker Compose. Terraform variables should mirror `.env.example` before production rollout.
