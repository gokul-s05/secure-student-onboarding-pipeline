output "raw_landing_bucket_name" {
  description = "Name of the D0 raw landing GCS bucket"
  value       = google_storage_bucket.raw_landing.name
}

output "staged_enforced_dataset_id" {
  description = "Full dataset ID of the D1 staged/enforced BigQuery dataset"
  value       = google_bigquery_dataset.staged_enforced.dataset_id
}

output "pipeline_service_account_email" {
  description = "Email of the least-privilege service account used by the CI/CD pipeline"
  value       = google_service_account.pipeline_sa.email
}
