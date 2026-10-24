mock_provider "aws" { override_during = plan }

variables {
  expected_account_id  = "111111111111"
  state_bucket_name    = "pixshare-state-test-fixture"
  notification_emails  = ["billing@example.invalid"]
  owner_verified_trial = true
}

run "bootstrap_keeps_recovery_state_private" {
  command = plan
  assert {
    condition     = !aws_s3_bucket.state.force_destroy && one(aws_s3_bucket_versioning.state.versioning_configuration).status == "Enabled"
    error_message = "Bootstrap state must be versioned and cannot be force-emptied."
  }
}

run "credits_do_not_hide_gross_cost" {
  command = plan
  module { source = "../modules/budget" }
  variables {
    name                = "fixture-budget"
    account_id          = "111111111111"
    notification_emails = ["billing@example.invalid"]
  }
  assert {
    condition = (
      aws_budgets_budget.gross.limit_amount == "20" &&
      !one(aws_budgets_budget.gross.cost_types).include_credit &&
      !one(aws_budgets_budget.gross.cost_types).include_refund &&
      one(aws_budgets_budget.gross.cost_types).include_tax &&
      length(aws_budgets_budget.gross.notification) == 4
    )
    error_message = "Gross spending alerts must exclude credits/refunds and notify before the $20 threshold."
  }
}
