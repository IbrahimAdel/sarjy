variable "do_token" {
  description = "DigitalOcean API token. Leave unset to use the DIGITALOCEAN_TOKEN environment variable."
  type        = string
  default     = null
  sensitive   = true
}

variable "app_name" {
  description = "Name of the App Platform app. Must be unique within the account."
  type        = string
  default     = "sarjy"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,30}[a-z0-9]$", var.app_name))
    error_message = "app_name must match ^[a-z][a-z0-9-]{0,30}[a-z0-9]$."
  }
}

variable "region" {
  description = "App Platform region slug, e.g. nyc, sfo, ams, sgp, lon, fra, tor, blr, syd."
  type        = string
  default     = "fra"
}

variable "project_name" {
  description = "Name of the DigitalOcean project that groups the app resources."
  type        = string
  default     = "sarjy"
}

variable "project_environment" {
  description = "Environment of the project's resources: Development, Staging, or Production."
  type        = string
  default     = "Production"

  validation {
    condition     = contains(["Development", "Staging", "Production"], var.project_environment)
    error_message = "project_environment must be Development, Staging, or Production."
  }
}

variable "github_repo" {
  description = "GitHub repository in owner/repo form. Requires DigitalOcean GitHub access."
  type        = string
  default     = "IbrahimAdel/sarjy"
}

variable "branch" {
  description = "Git branch to deploy."
  type        = string
  default     = "master"
}

variable "deploy_on_push" {
  description = "Automatically redeploy when the branch changes."
  type        = bool
  default     = false
}

variable "openai_api_key" {
  description = "OpenAI API key passed to the backend as an encrypted secret."
  type        = string
  sensitive   = true
}

variable "openai_model" {
  description = "OpenAI model used by the backend."
  type        = string
  default     = "gpt-4o-mini"
}



variable "stt_enabled" {
  description = "Enable local speech-to-text in the backend."
  type        = bool
  default     = true
}

variable "tts_enabled" {
  description = "Enable local text-to-speech in the backend."
  type        = bool
  default     = true
}

variable "tts_provider" {
  description = "TTS backend: piper or kokoro."
  type        = string
  default     = "piper"
}

variable "whisper_model" {
  description = "faster-whisper model name."
  type        = string
  default     = "base.en"
}

variable "log_level" {
  description = "Backend log level."
  type        = string
  default     = "INFO"
}

variable "log_format" {
  description = "Backend log format: text or json."
  type        = string
  default     = "json"
}
