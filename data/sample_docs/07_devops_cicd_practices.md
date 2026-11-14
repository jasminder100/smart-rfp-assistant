# NimbusEdge Technologies — DevOps and CI/CD Practices

**Document type:** Technical approach section for DevOps engagements (v1.5, 2025)

## Our DevOps Toolchain
- **Source control:** GitHub or GitLab, matching the client's choice.
- **CI/CD:** GitHub Actions, GitLab CI or Jenkins; Argo CD for GitOps deployments to Kubernetes.
- **Infrastructure as Code:** Terraform as the standard; AWS CloudFormation or Azure Bicep when the client requires it.
- **Containers:** Docker and Kubernetes (Amazon EKS, Azure AKS or Google GKE).
- **Observability:** Prometheus and Grafana for metrics, OpenTelemetry for tracing, and ELK or CloudWatch for logs.

## DevSecOps (Security Built into the Pipeline)
Every pipeline includes:
- Static code analysis (SAST) with SonarQube
- Dependency and container image scanning with Trivy
- Infrastructure-as-Code scanning with Checkov
- Secret detection with Gitleaks
A build fails automatically if a critical vulnerability is found.

## Kubernetes Governance
Policies are enforced with OPA Gatekeeper, for example blocking privileged containers, requiring resource limits and allowing images only from approved registries.

## Deployment Strategies
Blue/green and canary deployments, with automated rollback if error rates rise after a release.

## Typical Results
In past engagements, clients moved from monthly releases to multiple releases per week, and cut their average deployment time from about 3 hours to under 20 minutes.
