# Applies to Firebase client access; server SDK access continues to use IAM.
# Before apply, recheck the existing release and import it if another owner
# has published cloud.firestore since the read-only environment inspection.
resource "google_firebaserules_ruleset" "firestore" {
  project         = var.project_id
  deletion_policy = "ABANDON"

  source {
    files {
      name    = "firestore.rules"
      content = file("${path.module}/firestore.rules")
    }
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [google_project_service.required["firebaserules.googleapis.com"]]
}

resource "google_firebaserules_release" "firestore" {
  project         = var.project_id
  name            = "cloud.firestore"
  ruleset_name    = google_firebaserules_ruleset.firestore.name
  deletion_policy = "PREVENT"

  lifecycle {
    prevent_destroy = true
  }
}
