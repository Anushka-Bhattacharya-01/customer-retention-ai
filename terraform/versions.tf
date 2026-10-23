terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local state by default. For team use, switch to an S3 backend with DynamoDB locking:
  # backend "s3" {
  #   bucket         = "<state-bucket>"
  #   key            = "churn-mlops/terraform.tfstate"
  #   region         = "ap-south-1"
  #   dynamodb_table = "<lock-table>"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
