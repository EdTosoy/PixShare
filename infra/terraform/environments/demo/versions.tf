terraform {
  required_version = ">= 1.10.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.70.0"
    }
  }
  backend "s3" {
    region       = "ap-southeast-1"
    profile      = "pixshare-trial"
    key          = "pixshare/demo/terraform.tfstate"
    encrypt      = true
    use_lockfile = true
    # bucket and allowed_account_ids come from private backend.hcl.
  }
}
