variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Project name, used as a prefix for resource names"
  type        = string
  default     = "churn-mlops"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "enable_gpu_training" {
  description = "Create a GPU EC2 instance for model training (costs money while running)"
  type        = bool
  default     = false
}

variable "gpu_instance_type" {
  description = "GPU instance type for training"
  type        = string
  default     = "g4dn.xlarge"
}

variable "training_subnet_id" {
  description = "Private subnet for the training instance (required if enable_gpu_training = true)"
  type        = string
  default     = ""
}

variable "eks_oidc_provider_arn" {
  description = "OIDC provider ARN of an existing EKS cluster. If set, an IRSA role is created for the model API."
  type        = string
  default     = ""
}

variable "eks_oidc_provider_url" {
  description = "OIDC provider URL of the EKS cluster without https:// (for example oidc.eks.ap-south-1.amazonaws.com/id/XXXX)"
  type        = string
  default     = ""
}

variable "k8s_namespace" {
  description = "Kubernetes namespace where the model API runs"
  type        = string
  default     = "ml-serving"
}

variable "k8s_service_account" {
  description = "Kubernetes service account used by the model API"
  type        = string
  default     = "churn-api"
}

variable "bedrock_model_id" {
  description = "Amazon Bedrock model the assistant is allowed to call"
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}
