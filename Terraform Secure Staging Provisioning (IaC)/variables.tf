variable "project_id" {
  description = "GCP project ID for the staging environment"
  type        = string
  # JUDGMENT CALL: replace with the actual staging project ID before submission.
  # Using a placeholder here is fine in variables.tf (it's meant to be an input),
  # but do NOT leave it unset in a submitted terraform.tfvars.
}

variable "region" {
  description = "Primary GCP region for resources"
  type        = string
  default     = "us-central1"
  # JUDGMENT CALL: pick the region closest to your actual user base / lowest cost.
  # us-central1 is Google's cheapest general-purpose region, which is why I defaulted
  # to it for a staging environment — production might differ.
}

variable "environment" {
  description = "Deployment environment label, used for naming and lifecycle rules"
  type        = string
  default     = "staging"
}

variable "raw_landing_retention_days" {
  description = "Days to retain objects in the D0 raw landing bucket before auto-deletion"
  type        = number
  default     = 30
  # JUDGMENT CALL: 30 days assumes raw payloads are only needed transiently for
  # reprocessing/debugging before they're transformed into D1. If your onboarding
  # data has a compliance retention requirement, change this and say so out loud
  # in your presentation — that's a real judgment call panels want to see.
}

variable "pipeline_service_account_id" {
  description = "Account ID (not full email) for the least-privilege pipeline service account"
  type        = string
  default     = "onboarding-pipeline-sa"
}

variable "authorized_analytics_principal" {
  description = "Approved Google IAM principal allowed to query the enforced BigQuery dataset"
  type        = string
}
