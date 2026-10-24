provider "aws" {
  region              = "ap-southeast-1"
  profile             = "pixshare-trial"
  allowed_account_ids = [var.expected_account_id]
  default_tags {
    tags = {
      Project     = "PixShare"
      Environment = "demo"
      ManagedBy   = "Terraform"
      Release     = "7bcac0f151c6b4773533238dfe11b0b5fd4659b5"
    }
  }
}
