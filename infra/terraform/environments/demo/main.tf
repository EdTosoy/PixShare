resource "terraform_data" "preflight" {
  lifecycle {
    precondition {
      condition = (
        var.preflight.account_owner_confirmed && var.preflight.credits_and_expiry_confirmed &&
        var.preflight.required_services_confirmed && var.preflight.budget_notifications_verified &&
        var.preflight.production_configuration_ready &&
        var.preflight.estimated_gross_monthly_usd >= 12 && var.preflight.estimated_gross_monthly_usd < 20
      )
      error_message = "STOP: verify trial account, credits/expiry, service permissions, budget notifications, production configuration and gross monthly cost below $20."
    }
  }
}

module "lightsail" {
  source            = "../../modules/lightsail"
  name              = var.name
  public_key        = var.ssh_public_key
  admin_cidrs       = var.admin_cidrs
  blueprint_id      = var.blueprint_id
  bundle_id         = var.bundle_id
  availability_zone = var.availability_zone
  depends_on        = [terraform_data.preflight]
}

module "media" {
  source      = "../../modules/media"
  name        = var.name
  bucket_name = var.media_bucket_name
  server_ipv4 = module.lightsail.static_ipv4
  depends_on  = [terraform_data.preflight]
}
