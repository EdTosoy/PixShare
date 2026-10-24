mock_provider "aws" {
  override_during = plan
  mock_resource "aws_s3_bucket" {
    defaults = {
      arn                         = "arn:aws:s3:::pixshare-test-fixture"
      bucket_regional_domain_name = "pixshare-test-fixture.s3.ap-southeast-1.amazonaws.com"
    }
  }
  mock_resource "aws_cloudfront_distribution" {
    defaults = { arn = "arn:aws:cloudfront::111111111111:distribution/FIXTURE" }
  }
}

run "private_origin_and_scoped_credentials" {
  command = plan
  module { source = "../../modules/media" }
  variables {
    name        = "pixshare-fixture"
    bucket_name = "pixshare-test-fixture"
    server_ipv4 = "192.0.2.20"
  }
  assert {
    condition = (
      aws_s3_bucket_public_access_block.media.block_public_acls &&
      aws_s3_bucket_public_access_block.media.block_public_policy &&
      aws_s3_bucket_public_access_block.media.ignore_public_acls &&
      aws_s3_bucket_public_access_block.media.restrict_public_buckets &&
      !aws_s3_bucket.media.force_destroy
    )
    error_message = "The media bucket must remain private and cannot be forcibly emptied."
  }
  assert {
    condition     = one(aws_s3_bucket_versioning.media.versioning_configuration).status == "Enabled"
    error_message = "Recovery requires versioned media."
  }
  assert {
    condition     = aws_cloudfront_origin_access_control.media.signing_behavior == "always" && aws_cloudfront_origin_access_control.media.signing_protocol == "sigv4"
    error_message = "Origin reads must always be signed."
  }
  assert {
    condition     = one(aws_cloudfront_distribution.media.default_cache_behavior).allowed_methods == toset(["GET", "HEAD"])
    error_message = "CloudFront must never allow media mutations."
  }
  assert {
    condition = (
      jsondecode(aws_s3_bucket_policy.media.policy).Statement[1].Condition.StringEquals["AWS:SourceArn"] == "arn:aws:cloudfront::111111111111:distribution/FIXTURE" &&
      jsondecode(aws_s3_bucket_policy.media.policy).Statement[1].Resource == [
        "arn:aws:s3:::pixshare-test-fixture/pixshare/demo/*/original.*",
        "arn:aws:s3:::pixshare-test-fixture/pixshare/demo/*/variants/*.webp"
      ]
    )
    error_message = "Only this distribution's original/variant reads may be public; manifests/backups must stay private."
  }
  assert {
    condition = (
      jsondecode(aws_iam_user_policy.application.policy).Statement[0].Condition.IpAddress["aws:SourceIp"] == "192.0.2.20/32" &&
      jsondecode(aws_iam_user_policy.application.policy).Statement[0].Action == ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"] &&
      jsondecode(aws_iam_user_policy.application.policy).Statement[0].Resource == "arn:aws:s3:::pixshare-test-fixture/pixshare/demo/*"
    )
    error_message = "Application permissions must be restricted to media and the server's static IP."
  }
}
