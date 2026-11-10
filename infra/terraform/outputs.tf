output "repository_url" {
  description = "Docker repository URL."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.backend.repository_id}"
}

output "api_service_account" {
  value = google_service_account.api.email
}

output "api_url" {
  description = "Null until deploy_api=true; requires IAM authentication unless allow_public_api=true."
  value       = try(google_cloud_run_v2_service.api[0].uri, null)
}

output "api_public_access_enabled" {
  description = "Whether this configuration grants allUsers invocation on the deployed API."
  value       = var.deploy_api && var.allow_public_api
}
