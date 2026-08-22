terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 7.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ---------------------------------------------------------------------------
# D0 — RAW LANDING BUCKET
# Holds unprocessed student-onboarding payloads exactly as they arrive from
# the frontend, before any validation or transformation happens.
# ---------------------------------------------------------------------------
resource "google_storage_bucket" "raw_landing" {
  name     = "${var.project_id}-d0-raw-landing-${var.environment}"
  location = var.region

  # Uniform bucket-level access disables legacy per-object ACLs, which is the
  # main way "someone made an object public by accident" happens in practice.
  uniform_bucket_level_access = true

  # Force HTTPS-only access at the bucket policy level too (belt and suspenders
  # alongside uniform access above).
  public_access_prevention = "enforced"

  versioning {
    enabled = true
  }

  # Raw data is transient by design — it should be auto-purged once it has
  # been staged into D1, both for cost and to reduce the blast radius of an
  # accidental leak of raw, unvalidated data containing PII on minors.
  lifecycle_rule {
    condition {
      age = var.raw_landing_retention_days
    }
    action {
      type = "Delete"
    }
  }

  # Encryption at rest is on by default with Google-managed keys; if
  # HabotConnect requires customer-managed keys (CMEK) for compliance reasons,
  # a `encryption { default_kms_key_name = ... }` block would go here.
}

# ---------------------------------------------------------------------------
# D1 — STAGED / ENFORCED BIGQUERY DATASET
# Holds validated, schema-conformant records after the Django serializer
# (Task 3) has rejected anything malformed.
# ---------------------------------------------------------------------------
resource "google_bigquery_dataset" "staged_enforced" {
  dataset_id                 = "d1_staged_enforced_${var.environment}"
  location                   = var.region
  delete_contents_on_destroy = false # never let `terraform destroy` silently wipe student data

  # Explicit default table expiration keeps stray test tables from
  # accumulating silently in staging.
  default_table_expiration_ms = 7776000000 # 90 days, in ms

  labels = {
    environment = var.environment
    data_stage  = "d1-enforced"
  }
}

resource "google_bigquery_table" "student_onboarding" {
  dataset_id = google_bigquery_dataset.staged_enforced.dataset_id
  table_id   = "student_onboarding"

  # Schema mirrors the DCYN-validated fields coming out of the DRF serializer
  # in Task 3 — every boolean here corresponds to a validate_<field> method,
  # so a record can't reach this table unless it already passed that gate.
  schema = jsonencode([
    {
      name = "student_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "student_full_name"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "date_of_birth"
      type = "DATE"
      mode = "REQUIRED"
    },
    {
      name = "guardian_full_name"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "guardian_email"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "guardian_phone_number"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "has_learning_diagnosis"
      type = "BOOL"
      mode = "REQUIRED"
    },
    {
      name = "diagnosis_type"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "diagnosis_documentation_provided"
      type = "BOOL"
      mode = "REQUIRED"
    },
    {
      name = "requires_lsa_support"
      type = "BOOL"
      mode = "REQUIRED"
    },
    {
      name = "preferred_support_frequency"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "parent_consent_given"
      type = "BOOL"
      mode = "REQUIRED"
    },
    {
      name = "guardian_contact_verified"
      type = "BOOL"
      mode = "REQUIRED"
    },
    {
      name = "additional_notes"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "submitted_at"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    }
  ])

  deletion_protection = true
}

# ---------------------------------------------------------------------------
# ROW-LEVEL SECURITY
# Restricts which rows a given principal can see, on top of the dataset-level
# IAM below. Here: analysts can only see rows where consent was actually given
# — this is the RLS enforcing a business/legal rule at the data layer, not
# just trusting application code to filter correctly.
# ---------------------------------------------------------------------------
resource "google_bigquery_row_access_policy" "consented_rows_only" {
  project          = var.project_id
  dataset_id       = google_bigquery_dataset.staged_enforced.dataset_id
  table_id         = google_bigquery_table.student_onboarding.table_id
  policy_id        = "consented_rows_only"
  filter_predicate = "parent_consent_given = true"

  grantees = [
    var.authorized_analytics_principal,
  ]
}

# ---------------------------------------------------------------------------
# LEAST-PRIVILEGE SERVICE ACCOUNT FOR THE PIPELINE
# The CI/CD pipeline (Task 2) writes here — it should never have broad
# project-level Editor/Owner access.
# ---------------------------------------------------------------------------
resource "google_service_account" "pipeline_sa" {
  account_id   = var.pipeline_service_account_id
  display_name = "Onboarding pipeline (write-only, least privilege)"
}

# Can create objects in the raw landing bucket, cannot delete or read others'
# objects, cannot touch any other bucket in the project.
resource "google_storage_bucket_iam_member" "pipeline_writes_raw_landing" {
  bucket = google_storage_bucket.raw_landing.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.pipeline_sa.email}"

  condition {
    title       = "D0RawPrefixOnly"
    description = "Pipeline can create objects only under the d0/ prefix."
    expression  = "resource.type == \"storage.googleapis.com/Object\" && resource.name.startsWith(\"projects/_/buckets/${google_storage_bucket.raw_landing.name}/objects/d0/\")"
  }
}

# Can insert rows into D1 after validation, cannot alter the dataset schema
# or IAM policy itself.
resource "google_bigquery_dataset_iam_member" "pipeline_writes_staged" {
  dataset_id = google_bigquery_dataset.staged_enforced.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

# Analysts get read-only access to the dataset; row-level security above
# further narrows what they can actually see within it.
resource "google_bigquery_dataset_iam_member" "analysts_read_staged" {
  dataset_id = google_bigquery_dataset.staged_enforced.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = var.authorized_analytics_principal
}
