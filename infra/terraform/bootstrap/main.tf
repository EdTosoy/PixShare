provider "aws" {
  region              = "ap-southeast-1"
  profile             = "pixshare-trial"
  allowed_account_ids = [var.expected_account_id]
  default_tags {
    tags = { Project = "PixShare", Environment = "demo", ManagedBy = "Terraform" }
  }
}

variable "expected_account_id" {
  type        = string
  description = "Owner-confirmed trial account ID. Never use a personal account."
  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id)) && var.expected_account_id != "000000000000"
    error_message = "Supply the actual owner-confirmed trial account ID in an ignored tfvars file."
  }
}

variable "state_bucket_name" {
  type        = string
  description = "Globally unique, dedicated state bucket; no account ID needed in its name."
}

variable "notification_emails" {
  type        = set(string)
  sensitive   = true
  description = "Verified billing recipients, stored in private tfvars/state only."
  validation {
    condition     = length(var.notification_emails) > 0 && length(var.notification_emails) <= 10
    error_message = "Supply one to ten owner-approved billing notification addresses."
  }
}

variable "owner_verified_trial" {
  type        = bool
  default     = false
  description = "Set true only after owner/account/plan/credits/expiry/service checks."
}

resource "terraform_data" "approval" {
  lifecycle {
    precondition {
      condition     = var.owner_verified_trial
      error_message = "STOP: owner, trial credits/expiry and service eligibility must be verified before bootstrap."
    }
  }
}

module "budget" {
  source              = "../modules/budget"
  name                = "pixshare-demo-gross"
  account_id          = var.expected_account_id
  notification_emails = var.notification_emails
  depends_on          = [terraform_data.approval]
}

resource "aws_s3_bucket" "state" {
  bucket        = var.state_bucket_name
  force_destroy = false
  depends_on    = [module.budget]
  lifecycle { prevent_destroy = true }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "state" {
  bucket = aws_s3_bucket.state.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
    bucket_key_enabled = false
  }
}

resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "RequireTLS", Effect = "Deny", Principal = "*", Action = "s3:*"
      Resource  = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.state]
}

output "state_bucket" { value = aws_s3_bucket.state.id }
output "budget_name" { value = module.budget.name }
