terraform {
  required_providers { aws = { source = "hashicorp/aws" } }
}

variable "name" { type = string }
variable "account_id" { type = string }
variable "notification_emails" {
  type      = set(string)
  sensitive = true
}

resource "aws_budgets_budget" "gross" {
  account_id   = var.account_id
  name         = var.name
  budget_type  = "COST"
  limit_amount = "20"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"
  # Account-wide gross spend: credits/refunds must not hide consumption.
  cost_types {
    include_credit             = false
    include_refund             = false
    include_tax                = true
    include_subscription       = true
    include_support            = true
    include_upfront            = true
    include_recurring          = true
    include_other_subscription = true
    use_blended                = false
    use_amortized              = false
  }
  dynamic "notification" {
    for_each = toset([50, 80, 100])
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = var.notification_emails
    }
  }
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.notification_emails
  }
}

output "name" { value = aws_budgets_budget.gross.name }
