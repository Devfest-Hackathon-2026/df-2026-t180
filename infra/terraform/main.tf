locals {
  # Batch APIs are deferred until a working CLI and Firestore lock exist.
  services = toset([
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "iam.googleapis.com",
    "firestore.googleapis.com",
    "firebaserules.googleapis.com",
  ])
}

resource "google_project_service" "required" {
  for_each = local.services

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "backend" {
  project       = var.project_id
  location      = var.region
  repository_id = "hack26-backend"
  description   = "FastAPI runtime images"
  format        = "DOCKER"

  depends_on = [google_project_service.required]

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_service_account" "api" {
  project      = var.project_id
  account_id   = "hack26-api"
  display_name = "Regional Rules API runtime"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_custom_role" "post_writer" {
  project     = var.project_id
  role_id     = "hack26PostWriter"
  title       = "Regional Rules API data access"
  description = "Create, read and update API data with transactions; no delete permission."
  permissions = [
    "datastore.entities.create",
    "datastore.entities.get",
    "datastore.entities.list",
    "datastore.entities.update",
    "datastore.databases.get",
  ]

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "api_firestore" {
  project = var.project_id
  role    = google_project_iam_custom_role.post_writer.name
  member  = "serviceAccount:${google_service_account.api.email}"

  # IAM can scope to the existing database, but not to the posts collection.
  condition {
    title       = "default_database_only"
    description = "Limit document creation and reads to the existing default database."
    expression  = "resource.name == 'projects/${var.project_id}/databases/(default)'"
  }
}

resource "google_cloud_run_v2_service" "api" {
  count = var.deploy_api ? 1 : 0

  project             = var.project_id
  name                = "hack26-api"
  location            = var.region
  deletion_protection = true
  ingress             = "INGRESS_TRAFFIC_ALL"

  # Public invocation is opt-in through api_public_invoker below.
  template {
    service_account = google_service_account.api.email
    timeout         = "60s"

    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      image = var.api_image

      ports {
        container_port = 8080
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "FIREBASE_PROJECT_ID"
        value = var.project_id
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }
    }
  }

  depends_on = [google_project_iam_member.api_firestore, google_artifact_registry_repository.backend]
}

# This grant permits HTTP invocation only, not direct Firestore access.
resource "google_cloud_run_v2_service_iam_member" "api_public_invoker" {
  count = var.deploy_api && var.allow_public_api ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
