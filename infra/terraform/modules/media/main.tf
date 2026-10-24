terraform {
  required_providers { aws = { source = "hashicorp/aws" } }
}

variable "name" { type = string }
variable "bucket_name" { type = string }
variable "server_ipv4" { type = string }

locals {
  media_prefix  = "pixshare/demo"
  backup_prefix = "pixshare/backups"
}

resource "aws_s3_bucket" "media" {
  bucket        = var.bucket_name
  force_destroy = false
  lifecycle { prevent_destroy = true }
}
resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_ownership_controls" "media" {
  bucket = aws_s3_bucket.media.id
  rule { object_ownership = "BucketOwnerEnforced" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
    bucket_key_enabled = false
  }
}
resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_lifecycle_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"
    filter {}
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }
  rule {
    id     = "bounded-old-media-versions"
    status = "Enabled"
    filter { prefix = "${local.media_prefix}/" }
    noncurrent_version_expiration { noncurrent_days = 30 }
    expiration { expired_object_delete_marker = true }
  }
  rule {
    id     = "bounded-private-backups"
    status = "Enabled"
    filter { prefix = "${local.backup_prefix}/" }
    expiration { days = 14 }
    noncurrent_version_expiration { noncurrent_days = 30 }
  }
  depends_on = [aws_s3_bucket_versioning.media]
}

resource "aws_cloudfront_origin_access_control" "media" {
  name                              = var.name
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_response_headers_policy" "media" {
  name = var.name
  security_headers_config {
    content_type_options { override = true }
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = false
      preload                    = false
      override                   = true
    }
  }
}

resource "aws_cloudfront_distribution" "media" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "PixShare demo public images; origin and manifests remain private"
  price_class         = "PriceClass_200"
  http_version        = "http2and3"
  wait_for_deployment = true
  origin {
    domain_name              = aws_s3_bucket.media.bucket_regional_domain_name
    origin_id                = "media"
    origin_access_control_id = aws_cloudfront_origin_access_control.media.id
  }
  default_cache_behavior {
    target_origin_id           = "media"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    response_headers_policy_id = aws_cloudfront_response_headers_policy.media.id
    min_ttl                    = 0
    default_ttl                = 86400
    max_ttl                    = 31536000
    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }
  custom_error_response {
    error_code            = 403
    error_caching_min_ttl = 1
  }
  custom_error_response {
    error_code            = 404
    error_caching_min_ttl = 1
  }
  restrictions {
    geo_restriction { restriction_type = "none" }
  }
  viewer_certificate { cloudfront_default_certificate = true }
  depends_on = [aws_s3_bucket_public_access_block.media]
}

resource "aws_s3_bucket_policy" "media" {
  bucket = aws_s3_bucket.media.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "RequireTLS", Effect = "Deny", Principal = "*", Action = "s3:*"
        Resource  = [aws_s3_bucket.media.arn, "${aws_s3_bucket.media.arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
      {
        Sid       = "OnlyImagesThroughThisDistribution", Effect = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource = [
          "${aws_s3_bucket.media.arn}/${local.media_prefix}/*/original.*",
          "${aws_s3_bucket.media.arn}/${local.media_prefix}/*/variants/*.webp"
        ]
        Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.media.arn } }
      }
    ]
  })
}

# Lightsail has no EC2 instance-profile attachment. Create principals/policies
# ONLY. An operator provisions/rotates credentials outside Terraform/state.
resource "aws_iam_user" "application" {
  name          = "${var.name}-media"
  force_destroy = false
}
resource "aws_iam_user_policy" "application" {
  name = "media-only-from-server"
  user = aws_iam_user.application.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource  = "${aws_s3_bucket.media.arn}/${local.media_prefix}/*"
        Condition = { IpAddress = { "aws:SourceIp" = "${var.server_ipv4}/32" } }
      },
      {
        Effect = "Allow", Action = "s3:ListBucket", Resource = aws_s3_bucket.media.arn
        Condition = {
          StringLike = { "s3:prefix" = ["${local.media_prefix}/*"] }
          IpAddress  = { "aws:SourceIp" = "${var.server_ipv4}/32" }
        }
      }
    ]
  })
}

resource "aws_iam_user" "backup" {
  name          = "${var.name}-backup"
  force_destroy = false
}
resource "aws_iam_user_policy" "backup" {
  name = "private-backup-and-version-inventory"
  user = aws_iam_user.backup.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow", Action = ["s3:ListBucket", "s3:ListBucketVersions"], Resource = aws_s3_bucket.media.arn
        Condition = {
          StringLike = { "s3:prefix" = ["${local.media_prefix}/*", "${local.backup_prefix}/*"] }
          IpAddress  = { "aws:SourceIp" = "${var.server_ipv4}/32" }
        }
      },
      {
        Effect    = "Allow", Action = ["s3:GetObject", "s3:GetObjectVersion"]
        Resource  = ["${aws_s3_bucket.media.arn}/${local.media_prefix}/*", "${aws_s3_bucket.media.arn}/${local.backup_prefix}/*"]
        Condition = { IpAddress = { "aws:SourceIp" = "${var.server_ipv4}/32" } }
      },
      {
        Effect    = "Allow", Action = "s3:PutObject"
        Resource  = "${aws_s3_bucket.media.arn}/${local.backup_prefix}/*"
        Condition = { IpAddress = { "aws:SourceIp" = "${var.server_ipv4}/32" } }
      }
    ]
  })
}

output "bucket_name" { value = aws_s3_bucket.media.id }
output "https_origin" { value = "https://${aws_cloudfront_distribution.media.domain_name}" }
output "distribution_id" { value = aws_cloudfront_distribution.media.id }
output "application_user" { value = aws_iam_user.application.name }
output "backup_user" { value = aws_iam_user.backup.name }
