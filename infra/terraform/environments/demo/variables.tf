variable "expected_account_id" {
  type        = string
  description = "Owner-confirmed trial account ID; fixed AWS profile is pixshare-trial."
  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id)) && var.expected_account_id != "000000000000"
    error_message = "Supply the owner-confirmed trial account ID in a private tfvars file."
  }
}

variable "name" {
  type    = string
  default = "pixshare-demo"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.name))
    error_message = "Use a short lowercase resource name."
  }
}

variable "media_bucket_name" {
  type        = string
  description = "Unique bucket name without account IDs or private information."
  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.media_bucket_name))
    error_message = "Use a valid DNS bucket name without dots."
  }
}

variable "ssh_public_key" {
  type        = string
  description = "Existing operator public key only. Terraform never generates a private key."
  validation {
    condition     = can(regex("^ssh-(ed25519|rsa) [A-Za-z0-9+/=]+", var.ssh_public_key))
    error_message = "Supply an OpenSSH public key, never a private key."
  }
}

variable "admin_cidrs" {
  type        = set(string)
  description = "Specific operator IPv4 addresses; no unrestricted SSH."
  validation {
    condition     = length(var.admin_cidrs) > 0 && alltrue([for cidr in var.admin_cidrs : can(cidrnetmask(cidr)) && try(tonumber(split("/", cidr)[1]) >= 24, false)])
    error_message = "Restrict SSH to explicit IPv4 CIDRs /24 or narrower (prefer /32)."
  }
}

variable "blueprint_id" {
  type        = string
  default     = "ubuntu_24_04"
  description = "Verify current official Ubuntu blueprint availability before planning."
}

variable "bundle_id" {
  type        = string
  default     = "small_3_0"
  description = "Verify this is the $12, 2 GB, IPv4 Linux bundle with get-bundles."
  validation {
    condition     = var.bundle_id == "small_3_0"
    error_message = "This budgeted configuration permits only the reviewed 2 GB bundle."
  }
}

variable "availability_zone" {
  type    = string
  default = "ap-southeast-1a"
  validation {
    condition     = can(regex("^ap-southeast-1[a-z]$", var.availability_zone))
    error_message = "Only the Singapore region is authorized."
  }
}

variable "preflight" {
  description = "Private owner attestations; never set to true merely to produce a plan."
  type = object({
    account_owner_confirmed        = bool
    credits_and_expiry_confirmed   = bool
    required_services_confirmed    = bool
    budget_notifications_verified  = bool
    production_configuration_ready = bool
    estimated_gross_monthly_usd    = number
  })
  default = {
    account_owner_confirmed        = false
    credits_and_expiry_confirmed   = false
    required_services_confirmed    = false
    budget_notifications_verified  = false
    production_configuration_ready = false
    estimated_gross_monthly_usd    = 0
  }
}
