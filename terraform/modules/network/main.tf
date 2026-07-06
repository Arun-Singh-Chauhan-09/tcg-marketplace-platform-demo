# VPC with public/private subnets across 2 AZs; single NAT gateway (cost-optimized for demo).
variable "name" { type = string }
variable "vpc_cidr" { type = string }

data "aws_availability_zones" "available" { state = "available" }

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = { Name = var.name }
}

# ... subnets, IGW, single NAT, route tables (see terraform-aws-infra repo for full pattern)

output "vpc_id" { value = aws_vpc.this.id }
output "private_subnet_ids" { value = [] } # wire to aws_subnet.private[*].id
