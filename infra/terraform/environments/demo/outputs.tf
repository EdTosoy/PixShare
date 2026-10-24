output "api_static_ipv4" {
  value       = module.lightsail.static_ipv4
  description = "Set the API A record with the existing DNS owner; Terraform does not change DNS."
}
output "instance_name" { value = module.lightsail.instance_name }
output "media_bucket" { value = module.media.bucket_name }
output "media_https_origin" { value = module.media.https_origin }
output "distribution_id" { value = module.media.distribution_id }
output "application_storage_user" {
  value       = module.media.application_user
  description = "IAM user name only; provision and rotate keys OUTSIDE Terraform."
}
output "backup_storage_user" { value = module.media.backup_user }
