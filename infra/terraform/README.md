# PixShare demo infrastructure

Preparation only: no AWS resources have been created. The application release is
`7bcac0f151c6b4773533238dfe11b0b5fd4659b5`. Deployment tooling is a separate
revision; record both when publishing it. The later local title-display change
is intentionally outside this release.

Read [the complete deployment procedure](../../docs/TERRAFORM_DEPLOYMENT.md)
before using this configuration. It includes the remaining manual work, cost
assumptions, secrets, delivery approvals, restore drills and teardown.

```text
bootstrap/             Local initial state → private versioned state bucket + budget
environments/demo/     Singapore Lightsail + private media + CloudFront + IAM policies
modules/lightsail/     Host, imported public SSH key, static IPv4, restricted firewall
modules/media/         Private versioned S3, image-only OAC, separate IAM principals
modules/budget/        $20 gross account-wide monthly alerts (credits excluded)
```

Only `pixshare-trial` is configured. Both provider and remote backend require
the owner-confirmed account ID. There is no fallback profile, DNS provider,
generated SSH private key, IAM access-key resource, instance profile, DynamoDB,
managed database, load balancer or container orchestration service.

Local checks that do not contact AWS:

```sh
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/bootstrap init -backend=false -lockfile=readonly
terraform -chdir=infra/terraform/bootstrap validate
terraform -chdir=infra/terraform/bootstrap test
terraform -chdir=infra/terraform/environments/demo init -backend=false -lockfile=readonly
terraform -chdir=infra/terraform/environments/demo validate
terraform -chdir=infra/terraform/environments/demo test
```

The test plans use synthetic values and a mock provider. They establish
configuration invariants, not account eligibility, AWS permissions or a live
infrastructure plan. Provider checksums are retained in both root lockfiles;
`init -lockfile=readonly` prevents accidental upgrades. Initial downloads require
access to the official Terraform registry.

Private `terraform.tfvars`, `backend.hcl`, plans, state, `.terraform/`, working
environment files, credentials and backups are ignored. State can still contain
account metadata and notification emails: keep it private, encrypted and under
restricted administrative access. Never publish plan JSON or raw state.
