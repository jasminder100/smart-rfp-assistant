# NimbusEdge Technologies — Information Security Policy Summary for Clients

**Document type:** Security compliance response pack (approved by CISO office, v5.0, March 2026)

## 1. Data Encryption
- **Data at rest:** All client data at rest is encrypted using AES-256. On AWS we use AWS KMS with customer-managed keys (CMKs); on Azure we use Azure Key Vault.
- **Key rotation:** Encryption keys are rotated automatically every 365 days, or immediately if a compromise is suspected.
- **Data in transit:** All data in transit is encrypted with TLS 1.2 or higher. TLS 1.0 and 1.1 are disabled on all endpoints we manage.
- **Backups:** Backups are encrypted with the same AES-256 standard and stored in a separate account or subscription.

## 2. Identity and Access Management
- Role-based access control (RBAC) following the principle of least privilege.
- Multi-factor authentication (MFA) is mandatory for all employees and for all access to client environments.
- Privileged access is granted through a Privileged Access Management (PAM) tool with just-in-time access that expires after 8 hours.
- Access reviews are performed quarterly. Access for departing employees is revoked within 4 hours of their exit.

## 3. Vulnerability Management
- Infrastructure and container images are scanned weekly.
- Critical vulnerabilities (CVSS 9.0 and above) are patched within 72 hours; high vulnerabilities within 7 days.
- An independent third-party penetration test is carried out once a year, and after any major release on request.

## 4. Security Monitoring
- 24x7 Security Operations Centre (SOC) operated from our Pune delivery centre.
- Centralized logging with SIEM; security logs are retained for 1 year.

## 5. Employee Security
- Background verification for all employees before onboarding.
- Mandatory security awareness training every 6 months, including phishing simulations.

## 6. Certifications
ISO/IEC 27001:2022 and SOC 2 Type II. Certificates and the SOC 2 report are shared with clients under NDA.
