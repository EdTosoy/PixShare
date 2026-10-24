mock_provider "aws" { override_during = plan }

run "only_web_and_restricted_ssh" {
  command = plan
  module { source = "../../modules/lightsail" }
  variables {
    name              = "pixshare-fixture"
    public_key        = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestFixtureOnly"
    admin_cidrs       = ["192.0.2.10/32"]
    blueprint_id      = "ubuntu_24_04"
    bundle_id         = "small_3_0"
    availability_zone = "ap-southeast-1a"
  }
  assert {
    condition = (
      length(aws_lightsail_instance_public_ports.api.port_info) == 3 &&
      alltrue([for p in aws_lightsail_instance_public_ports.api.port_info : p.from_port == p.to_port && contains([22, 80, 443], p.from_port)]) &&
      alltrue([for p in aws_lightsail_instance_public_ports.api.port_info : p.from_port != 22 || p.cidrs == toset(["192.0.2.10/32"])])
    )
    error_message = "Only HTTP/HTTPS and explicitly restricted SSH may be reachable; database/API ports stay private."
  }
}
