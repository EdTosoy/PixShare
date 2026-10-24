# Synthetic values and a mock provider: these tests never authenticate to AWS.
mock_provider "aws" {
  override_during = plan
  mock_resource "aws_lightsail_static_ip" {
    defaults = { ip_address = "192.0.2.20" }
  }
}

variables {
  expected_account_id = "111111111111"
  media_bucket_name   = "pixshare-test-fixture"
  ssh_public_key      = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestFixtureOnly"
  admin_cidrs         = ["192.0.2.10/32"]
}

run "unverified_preflight_is_rejected" {
  command         = plan
  expect_failures = [terraform_data.preflight]
}

run "unrestricted_administration_is_rejected" {
  command = plan
  variables { admin_cidrs = ["0.0.0.0/0"] }
  expect_failures = [var.admin_cidrs, terraform_data.preflight]
}

run "over_budget_is_rejected" {
  command = plan
  variables {
    preflight = {
      account_owner_confirmed        = true
      credits_and_expiry_confirmed   = true
      required_services_confirmed    = true
      budget_notifications_verified  = true
      production_configuration_ready = true
      estimated_gross_monthly_usd    = 20
    }
  }
  expect_failures = [terraform_data.preflight]
}

run "approved_fixture_plans" {
  command = plan
  variables {
    preflight = {
      account_owner_confirmed        = true
      credits_and_expiry_confirmed   = true
      required_services_confirmed    = true
      budget_notifications_verified  = true
      production_configuration_ready = true
      estimated_gross_monthly_usd    = 16
    }
  }
  assert {
    condition     = output.api_static_ipv4 == "192.0.2.20"
    error_message = "The API DNS output must use the attached static IP."
  }
}
