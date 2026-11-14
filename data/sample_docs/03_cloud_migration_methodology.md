# NimbusEdge Technologies — Cloud Migration Methodology ("NimbusPath")

**Document type:** Technical approach section reused in migration proposals (v2.4, 2025)

## Overview
NimbusPath is our five-phase framework for migrating workloads to the cloud with minimal downtime and controlled cost.

## Phase 1: Discover (2–4 weeks)
Automated discovery of servers, applications and dependencies using AWS Application Discovery Service or Azure Migrate. Output: a complete application inventory and dependency map.

## Phase 2: Assess and Plan (2–3 weeks)
Each application is assigned one of the "7 Rs" strategies: Retire, Retain, Rehost, Relocate, Repurchase, Replatform or Refactor. We build a total cost of ownership (TCO) comparison and a wave plan that groups applications into migration waves of 10–25 applications each.

## Phase 3: Build the Landing Zone (2–4 weeks)
A secure multi-account landing zone built with Terraform, including networking, identity, logging, guardrails and cost tagging. On AWS we follow AWS Control Tower and the Well-Architected Framework.

## Phase 4: Migrate in Waves
- Rehost migrations use AWS Application Migration Service (MGN) or Azure Migrate.
- Databases are migrated with AWS Database Migration Service (DMS), using continuous replication so cutover downtime is typically under 30 minutes.
- Every wave has a tested rollback plan and a go/no-go checkpoint.

## Phase 5: Optimize and Hand Over
Right-sizing, Savings Plans or Reserved Instance recommendations, and FinOps dashboards. Clients typically see 25–35% lower infrastructure cost within six months of migration. Includes 30 days of hypercare after the final wave.

## Governance
A weekly steering report and a migration RAID log (Risks, Assumptions, Issues, Dependencies) are shared with the client.
