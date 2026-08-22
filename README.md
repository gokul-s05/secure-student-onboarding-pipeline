# Secure Student Onboarding Data Pipeline

## Junior Cloud & DevOps Engineer Project

**Candidate:** Gokul S  
**Project:** Secure Student Onboarding Data Pipeline  
**Focus:** GCP • Terraform • GitHub Actions • Gitleaks • Django REST Framework • DCYN • BigQuery

---

## 1. Project Overview

This project implements a secure student-onboarding data pipeline designed to prevent invalid, ambiguous, or insecure data from progressing into the staging and analytics layers.

The solution combines:

- Django REST Framework validation
- DCYN strict Boolean normalization
- Google Cloud Storage (GCS)
- Google BigQuery
- Terraform Infrastructure as Code
- GitHub Actions
- Gitleaks secret scanning
- Fail-closed CI/CD build gates
- Quarantine handling for failed builds
- Least-privilege IAM
- BigQuery Row-Level Security

The core design principle is **Poka-Yoke (mistake-proofing)**: invalid data and non-compliant code should be rejected automatically rather than relying on manual review.

---

## 2. Architecture

```text
Raw Student Onboarding Payload
            │
            ▼
     D0 Raw Landing
      Google Cloud Storage
            │
            ▼
     Django REST Framework
            │
            ▼
       DCYN Validation
            │
            ├── Invalid / Ambiguous → REJECT
            │
            ▼
     Business Rule Validation
            │
            ▼
       D1 Staged Data
        BigQuery Dataset
            │
            ▼
        Analytics
```

CI/CD control plane:

```text
Git / Pull Request
       │
       ▼
GitHub Actions
       │
       ├── Python Formatting
       ├── Python Linting
       ├── Python Tests
       ├── Terraform Format
       ├── Terraform Init
       ├── Terraform Validate
       ├── Gitleaks
       │
       ▼
  Fail-Closed Build Gate
       │
       ├── PASS → Proceed
       │
       └── FAIL → Quarantine
                    │
                    ├── PR Label
                    └── Non-zero Exit
```

---

## 3. Repository Structure

```text
.
├── README.md
├── Poka-Yoke Automated CICD Build Gate/
│   ├── .gitleaks.toml
│   └── build-gate.yml
├── Schema Mapping and DCYN Validation/
│   ├── dcyn.py
│   ├── models.py
│   ├── sample_raw_payload.json
│   ├── schema_mapping.xlsx
│   ├── serializers.py
│   └── test_validation.py
└── Terraform Secure Staging Provisioning (IaC)/
    ├── .terraform.lock.hcl
    ├── main.tf
    ├── outputs.tf
    ├── terraform.tfvars.example
    └── variables.tf
```

---

## 4. Terraform Infrastructure

Terraform defines the GCP staging infrastructure and security controls.

### Main infrastructure components

- Google Cloud Storage raw landing bucket
- BigQuery staged/enforced dataset
- BigQuery student onboarding table
- BigQuery Row-Level Security policy
- Pipeline service account
- Least-privilege IAM permissions
- Analytics read access
- Lifecycle retention for raw data
- Public access prevention
- Uniform bucket-level access
- Object prefix restrictions

The Terraform configuration is contained in:

```text
Terraform Secure Staging Provisioning (IaC)/
```

---

## 5. D0 — Raw Landing Layer

The D0 layer is designed to temporarily hold unprocessed onboarding payloads.

Security controls defined in Terraform include:

- Uniform bucket-level access
- Public access prevention
- Object versioning
- Lifecycle-based retention
- Prefix-restricted object creation
- Least-privilege pipeline access

Raw data is intended to be retained temporarily before validation and staging.

---

## 6. D1 — Staged / Enforced Layer

Validated records are designed to enter the D1 BigQuery staging layer.

The BigQuery schema includes:

- `student_id`
- `student_full_name`
- `date_of_birth`
- `guardian_full_name`
- `guardian_email`
- `guardian_phone_number`
- `has_learning_diagnosis`
- `diagnosis_type`
- `diagnosis_documentation_provided`
- `requires_lsa_support`
- `preferred_support_frequency`
- `parent_consent_given`
- `guardian_contact_verified`
- `additional_notes`
- `submitted_at`

The table uses required and nullable modes to enforce the intended schema.

---

## 7. Row-Level Security

Terraform defines a BigQuery Row-Level Security policy using:

```text
parent_consent_given = true
```

This is intended to ensure that authorized analytics users can only access rows where the required parent consent condition is satisfied.

The security model combines:

```text
Dataset IAM
     +
Row-Level Security
     =
Least-privilege data access
```

---

## 8. Least-Privilege IAM

A dedicated pipeline service account is defined for the CI/CD/data pipeline.

The design avoids broad project-level Owner or Editor permissions.

The pipeline service account is granted only the permissions required for its intended operations, including:

- Creating objects in the raw landing area
- Writing validated records to the staged BigQuery dataset

Analytics access is separately defined as read-only.

---

## 9. Django REST Framework + DCYN Validation

The onboarding serializer performs field-level and cross-field validation.

Raw JSON fields are mapped to Django model fields. Examples:

```text
has_existing_learning_diagnosis
        ↓
has_learning_diagnosis

diagnosis_documentation_uploaded
        ↓
diagnosis_documentation_provided

requires_learning_support_assistant
        ↓
requires_lsa_support
```

The serializer also validates:

- Required fields
- Name length
- Email format
- E.164 phone number format
- Date fields
- Boolean values
- Diagnosis documentation
- Parent consent
- Learning support requirements
- Additional notes length

---

## 10. DCYN Strict Boolean Validation

Five binary fields are processed through DCYN before normal DRF validation.

Controlled behavior:

```text
Yes       → True
No        → False

Pending   → REJECT
N/A       → REJECT
Maybe     → REJECT
Empty     → REJECT
```

The principle is:

```text
INVALID ≠ FALSE
```

Ambiguous values are rejected instead of being guessed or silently converted.

This prevents logically incorrect records from entering the staging layer.

---

## 11. Cross-Field Business Rules

### Rule 1 — Learning support requires consent

If:

```text
requires_lsa_support = True
```

then:

```text
parent_consent_given = True
```

must also be satisfied.

Otherwise the record is rejected.

### Rule 2 — Existing diagnosis requires documentation

If:

```text
has_learning_diagnosis = True
```

then:

```text
diagnosis_documentation_provided = True
```

must be satisfied.

Otherwise the record is rejected.

---

## 12. Poka-Yoke CI/CD Build Gate

The GitHub Actions workflow implements a fail-closed build gate.

The workflow performs:

1. Python formatting
2. Python linting
3. Python tests
4. Terraform formatting check
5. Terraform initialization
6. Terraform validation
7. Gitleaks secret scanning
8. Fail-closed build gate

The build gate depends on all required validation jobs. A failed validation prevents the gate from opening.

---

## 13. Quarantine Logic

If one or more required validation jobs fail, the quarantine job runs.

The quarantine workflow:

1. Detects the failed validation
2. Labels the pull request
3. Applies:
   - `quarantined`
   - `failed-build-gate`
4. Exits with a non-zero status

```text
All checks pass
      │
      ▼
 Build Gate
      │
      ▼
 Proceed

Any check fails
      │
      ▼
 Quarantine
      │
      ├── PR labelled
      └── Workflow fails
```

---

## 14. Gitleaks Secret Scanning

Gitleaks is configured using:

```text
Poka-Yoke Automated CICD Build Gate/.gitleaks.toml
```

The configuration extends the default Gitleaks ruleset with project-specific rules.

### Custom Django rule

The project defines a rule for detecting hardcoded Django:

```text
SECRET_KEY
```

### GCP credential detection

A custom pattern is also included for embedded GCP service-account private keys.

### Validation

A controlled test secret was temporarily introduced and scanned using the custom Django rule.

The scanner detected the secret and returned a failure.

Expected behavior:

```text
Secret detected
      ↓
Gitleaks fails
      ↓
Build gate remains closed
```

The temporary test secret was removed before final project packaging.

---

## 15. Testing

The Python validation suite was executed using:

```powershell
python -m pytest -q
```

Result:

```text
18 passed
```

Terraform validation was executed with:

```text
terraform fmt       ✓
terraform validate  ✓
terraform plan      ✓
```

The Gitleaks custom rule was separately verified using a controlled test.

---

## 16. Terraform Deployment Limitation

The Terraform configuration was validated successfully and a Terraform plan was generated.

However, actual infrastructure deployment was blocked by an external GCP project prerequisite.

During:

```text
terraform apply
```

GCP returned:

```text
Error 403:
The billing account for the owning project is disabled
in state closed, accountDisabled
```

BigQuery also reported that billing had not been enabled for the project.

### Important distinction

This was **not a Terraform configuration validation failure**.

Observed result:

```text
terraform fmt       → PASSED
terraform validate  → PASSED
terraform plan      → GENERATED
terraform apply     → BLOCKED
```

The deployment limitation was caused by the assigned GCP project's billing status.

Therefore, the Terraform files describe the intended infrastructure and security configuration, but the project does not claim successful deployment of resources that could not be provisioned because of this external billing restriction.

---

## 17. Security Design Summary

```text
Source Code
    │
    ├── Gitleaks
    │
    ▼
CI/CD
    │
    ├── Lint
    ├── Tests
    ├── Terraform Validation
    └── Fail-Closed Gate
    │
    ▼
Data Ingestion
    │
    ├── DCYN
    ├── DRF Validation
    └── Business Rules
    │
    ▼
GCP Data Layer
    │
    ├── IAM
    ├── Public Access Prevention
    ├── Least Privilege
    └── BigQuery Row-Level Security
```

---

## 18. Key Engineering Outcomes

### Security

Implemented secret scanning, least-privilege IAM design, public-access prevention and consent-aware data access controls.

### Reliability

Implemented fail-closed CI/CD behavior so validation failures cannot silently progress.

### Infrastructure

Defined reproducible GCP infrastructure using Terraform Infrastructure as Code.

### Data Quality

Implemented strict Boolean handling, schema validation and cross-field business rules before staging.

---

## 19. Technologies Used

### Cloud

- Google Cloud Platform
- Google Cloud Storage
- Google BigQuery
- IAM

### Infrastructure as Code

- Terraform

### CI/CD

- GitHub Actions
- Poka-Yoke / fail-closed build gate
- Gitleaks

### Backend / Validation

- Python
- Django
- Django REST Framework
- DCYN
- Pytest

### Data / Schema

- JSON
- Excel schema mapping

---

## 20. How to Validate Locally

### Python tests

From:

```text
Schema Mapping and DCYN Validation
```

run:

```powershell
python -m pytest -q
```

### Terraform

From:

```text
Terraform Secure Staging Provisioning (IaC)
```

run:

```powershell
terraform init
terraform fmt -check
terraform validate
terraform plan
```

A valid GCP project with billing enabled is required for actual infrastructure provisioning.

### Gitleaks

From the project root:

```powershell
gitleaks dir "." --config ".\Poka-Yoke Automated CICD Build Gate\.gitleaks.toml"
```

---

## 21. Configuration

Do not commit real GCP credentials, secrets, or environment-specific Terraform variables.

Use:

```text
terraform.tfvars.example
```

as the configuration template.

For local execution, create a `terraform.tfvars` file with the appropriate project-specific values.

The real `terraform.tfvars` file is intentionally excluded from the submission.

---

## 22. Project Evidence

The project presentation contains evidence for:

- Python test execution
- Gitleaks custom rule detection
- Terraform validation
- Terraform planning
- Terraform deployment limitation
- DCYN validation behavior
- CI/CD quarantine logic

The presentation is supporting evidence for the implementation contained in this repository.

---

## 23. Final Status

```text
Python Validation       ✓ Completed
DCYN Validation         ✓ Completed
Gitleaks Configuration  ✓ Completed
CI/CD Build Gate        ✓ Completed
Quarantine Logic        ✓ Completed
Terraform Configuration ✓ Validated
Terraform Plan          ✓ Generated
GCP Infrastructure      ⚠ Deployment blocked by billing
Presentation            ✓ Completed
```

---

## Final Statement

The project demonstrates a secure, fail-closed cloud data pipeline in which invalid data, ambiguous Boolean values, hardcoded secrets, and non-compliant infrastructure changes are prevented from progressing through the system by automated validation and security controls.
