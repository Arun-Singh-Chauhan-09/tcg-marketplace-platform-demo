# EKS cluster + managed node group with IRSA enabled.
variable "name" { type = string }
variable "vpc_id" { type = string }
variable "private_subnets" { type = list(string) }
variable "instance_types" { type = list(string) }
variable "capacity_type" { type = string }
variable "desired_size" { type = number }

# Skeleton: aws_eks_cluster + aws_eks_node_group + OIDC provider for IRSA.
# Full working pattern lives in my lemon-brokerage-platform-demo repo; kept
# minimal here to stay within demo AWS budget.
