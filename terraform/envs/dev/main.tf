terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  # backend "s3" {}   # configure per environment
}

provider "aws" {
  region = var.region
}

module "network" {
  source   = "../../modules/network"
  name     = var.name
  vpc_cidr = "10.60.0.0/16"
}

module "eks" {
  source          = "../../modules/eks"
  name            = var.name
  vpc_id          = module.network.vpc_id
  private_subnets = module.network.private_subnet_ids

  # Demo-sized and cheap: 2x t3.medium SPOT. Documented trade-off vs prod on-demand.
  instance_types = ["t3.medium"]
  capacity_type  = "SPOT"
  desired_size   = 2
}

resource "aws_ecr_repository" "app" {
  name                 = "${var.name}/tcg-marketplace"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration { scan_on_push = true }
}
