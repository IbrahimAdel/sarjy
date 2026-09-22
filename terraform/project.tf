resource "digitalocean_project" "sarjy" {
  name        = var.project_name
  description = "Sarjy voice assistant resources."
  purpose     = "Web Application"
  environment = var.project_environment
}
