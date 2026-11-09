variable "project_id" {
  description = "Existing GCP project; never created by this configuration."
  type        = string
  default     = "hack26-project"
}

variable "region" {
  description = "Cloud Run and Artifact Registry region, aligned with existing Firestore."
  type        = string
  default     = "asia-northeast1"
}

variable "deploy_api" {
  description = "Keep false for bootstrap; set true only after pushing api_image."
  type        = bool
  default     = false
}

variable "allow_public_api" {
  description = "Allow unauthenticated HTTP invocation. Keep false until all deployed admin routes have verified authentication and authorization."
  type        = bool
  default     = false
}

variable "api_image" {
  description = "Immutable Artifact Registry image digest, required when deploy_api=true."
  type        = string
  default     = ""

  validation {
    condition     = !var.deploy_api || can(regex("^${var.region}-docker\\.pkg\\.dev/${var.project_id}/hack26-backend/fastapi@sha256:[0-9a-f]{64}$", var.api_image))
    error_message = "Set api_image to the pushed fastapi image URI with a sha256 digest in this project's hack26-backend repository."
  }
}
