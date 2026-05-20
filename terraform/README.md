# ComplianceGuard Terraform

Infrastructure-as-Code structure for deploying ComplianceGuard to cloud environments.

## Structure

```
terraform/
├── modules/
│   ├── vpc/           # Network isolation
│   ├── rds/           # PostgreSQL 15
│   ├── elasticache/   # Redis cluster
│   ├── ecs/           # Container orchestration (or EKS reference)
│   └── secrets/       # Vault/AWS Secrets Manager integration
└── environments/
    ├── staging/
    └── production/
```

## Usage

```bash
cd environments/production
terraform init
terraform plan -var-file=production.tfvars
terraform apply
```

## Security Requirements

- Enable encryption at rest for RDS and Redis
- Deploy scan workers in isolated subnet with no internet gateway
- Use AWS Secrets Manager or HashiCorp Vault for `SECRET_KEY`, `FIELD_ENCRYPTION_KEY`
- Enable VPC flow logs and CloudTrail
- WAF in front of ALB with rate limiting rules

## Variables (production.tfvars example)

```hcl
environment         = "production"
domain_name         = "app.complianceguard.io"
db_instance_class   = "db.r6g.large"
redis_node_type     = "cache.r6g.large"
enable_vault        = true
scan_subnet_isolated = true
```
