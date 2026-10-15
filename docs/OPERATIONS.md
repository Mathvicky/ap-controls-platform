# Operating and extending the platform

## Incident runbook

1. Record UTC start time, affected environment, task definition revision, recent changes and customer impact. Assign an incident lead and communications owner.
2. Inspect ECS service events, running task count, stopped-task reasons and `/ecs/ap-controls` logs. A CPU alert alone is not proof of outage; missing CPU metrics may indicate zero tasks and need a separate availability alarm.
3. For startup failures, check ECR connectivity, execution-role permissions, secret access, database connectivity and schema initialization. Never print database secrets into logs.
4. For a bad release, restore the previous image digest in Terraform, review and apply. Do not roll back destructive database migrations automatically.
5. For database saturation, inspect connections, locks, slow queries and storage. Stop expensive batch work, then scale only after confirming the bottleneck. Do not restart the database as the first response.
6. Verify readiness and synthetic duplicate detection, then record recovery time and follow-up actions. The current project has no paging integration or automated incident responder.

## Database practice

The demo creates one table at startup. Before production introduce versioned migrations executed as a separate deployment job; use expand/contract changes and lock timeouts. The `(vendor, reference)` primary key supports current duplicate checks. Use `EXPLAIN (ANALYZE, BUFFERS)` on representative synthetic data before adding indexes. Partition only after measured table growth and query patterns justify it; preserve uniqueness across partitions deliberately.

Backups retain seven days with RDS point-in-time recovery. Define business-approved RPO/RTO and perform a restore drill into a new isolated instance: select restore timestamp, restore with private security groups, verify row counts and representative queries, run synthetic assessment, record elapsed recovery, then switch connection configuration during a controlled cutover. A successful backup is not a demonstrated restore.

Deletion protection and a final snapshot protect the example. To tear down your own demo, first review retained data and snapshots, intentionally disable deletion protection through Terraform, apply that change, then review a destroy plan. Repeated final snapshot names may collide: choose a unique identifier. Retained snapshots, ECR images and external VPC resources may still cost money.

## Reliability roadmap

Proposed targets, not achieved measurements: 99.9% successful valid assessments over 30 days and p95 latency below 300 ms at an agreed request rate. Add request latency, error count, request volume, running task count, RDS free storage/connections and synthetic readiness monitoring. Alert on sustained error-budget burn; route to an on-call service with an owner and escalation policy. Test database failure, broken image rollback and lost network connectivity in staging.

Add a private ALB with HTTPS and identity-aware ingress, two or more task replicas, target tracking with explicit limits, connection pooling and application database roles. Load-test before selecting instance sizes. Review AWS spend by tags; include RDS Multi-AZ, NAT, logs, Fargate and backups in the cost estimate.

## ML operations extension

`rules-v1` is deterministic and deliberately transparent. To add ML, train offline on synthetic or properly approved data; version dataset, feature contract, evaluation metrics and model artifact. Store immutable artifacts in S3 with encryption and scoped access. Separate training IAM and compute from serving. Gate promotion on precision/recall, false-positive costs, latency and reproducibility. Shadow a new model before canary promotion, monitor feature drift and review rates, and keep the previous artifact for rollback. No ML training or model registry is implemented here.

## ECS versus EKS

ECS/Fargate keeps the starter operationally small. An EKS extension should preserve the same database and image contracts while adding workload identity, namespace policies, admission policies, resource limits, probes, disruption budgets and node upgrades. Do not run both orchestrators merely to list technologies on a CV.

## Security and delivery

GitHub CI has read-only repository permissions. The publishing workflow requests OIDC only for its manual job. Configure the AWS role trust with audience `sts.amazonaws.com` and exact subject `repo:OWNER/REPO:environment:portfolio`; restrict the GitHub environment to the main branch and require reviewers. Grant that role only ECR authorization plus layer upload and PutImage on your repository. No Terraform administrator permissions are needed to publish images.

Before production pin all Actions to reviewed commit SHAs, generate an SBOM, scan dependencies/images/IaC, add CodeQL or equivalent and resolve actionable findings. Add automated PostgreSQL integration tests and schema migration checks. The current CI is a verification baseline, not a complete DevSecOps programme.
