terraform {
  required_providers { aws = { source = "hashicorp/aws" } }
}

variable "name" { type = string }
variable "public_key" { type = string }
variable "admin_cidrs" { type = set(string) }
variable "blueprint_id" { type = string }
variable "bundle_id" { type = string }
variable "availability_zone" { type = string }

resource "aws_lightsail_key_pair" "admin" {
  name       = "${var.name}-admin"
  public_key = var.public_key
}

resource "aws_lightsail_instance" "api" {
  name              = var.name
  availability_zone = var.availability_zone
  blueprint_id      = var.blueprint_id
  bundle_id         = var.bundle_id
  ip_address_type   = "ipv4"
  key_pair_name     = aws_lightsail_key_pair.admin.name
  user_data         = file("${path.module}/bootstrap.sh")
  # The included disk holds PostgreSQL. Teardown requires an explicit backup review.
  lifecycle { prevent_destroy = true }
}

resource "aws_lightsail_static_ip" "api" { name = var.name }
resource "aws_lightsail_static_ip_attachment" "api" {
  static_ip_name = aws_lightsail_static_ip.api.name
  instance_name  = aws_lightsail_instance.api.name
}

resource "aws_lightsail_instance_public_ports" "api" {
  instance_name = aws_lightsail_instance.api.name
  port_info {
    protocol          = "tcp"
    from_port         = 80
    to_port           = 80
    cidrs             = ["0.0.0.0/0"]
    cidr_list_aliases = []
    ipv6_cidrs        = []
  }
  port_info {
    protocol          = "tcp"
    from_port         = 443
    to_port           = 443
    cidrs             = ["0.0.0.0/0"]
    cidr_list_aliases = []
    ipv6_cidrs        = []
  }
  port_info {
    protocol          = "tcp"
    from_port         = 22
    to_port           = 22
    cidrs             = var.admin_cidrs
    cidr_list_aliases = []
    ipv6_cidrs        = []
  }
}

output "instance_name" { value = aws_lightsail_instance.api.name }
output "static_ipv4" { value = aws_lightsail_static_ip.api.ip_address }
