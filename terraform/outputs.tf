output "app_id" {
  description = "App Platform application ID."
  value       = digitalocean_app.sarjy.id
}

output "project_id" {
  description = "DigitalOcean project ID grouping the app resources."
  value       = digitalocean_project.sarjy.id
}

output "default_ingress" {
  description = "Default ondigitalocean.app URL of the app."
  value       = digitalocean_app.sarjy.default_ingress
}

output "live_url" {
  description = "Live URL of the app."
  value       = digitalocean_app.sarjy.live_url
}
